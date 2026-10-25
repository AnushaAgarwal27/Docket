"""The layer between Docket's agents and anything a person sees or hears.

The Fetch.ai agents decide *what* is true: they run the rules, hold the Hearing, open cases, research
the news. This module decides *what may be said about it, to whom, in what form*. Nothing reaches a
student, a payroll office or a phone line without passing through here.

Three jobs, in order:

1. REDACT. Each audience gets its own slice of the facts, built by allow-list. Payroll never receives
   work hours, bank rows, an arrival date or another student's name, because those keys are not in
   its slice; there is nothing to leak. A group audience gets counts and totals only.

2. CONVERT. Claude turns the redacted facts into words for one channel: a sentence a voice agent can
   speak, a text short enough to send, a chat reply, a paragraph for a document. Claude never gets a
   fact its audience is not allowed to see, and is told it may not do arithmetic or invent a rule.

3. CHECK. Code reads what Claude wrote and rejects it unless every dollar amount appears in the
   facts, every quoted sentence is word for word in a verified source, no phone number appears that
   we did not supply, no redacted term leaked back in, and the text fits the channel. A rejected
   render falls back to a sentence written entirely in code, so a refusal degrades to something
   plainer rather than to nothing.

The checks are the point. Claude writes the words; it never decides the money, the rule or the
recipient, and it cannot widen its own audience.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Literal

from rules.quote_checker import check_quote

MODEL = "claude-opus-5"

Channel = Literal["voice", "sms", "chat", "document"]
Audience = Literal["student", "payroll", "group", "public"]

# How long a message may be on each channel, and what it may contain. Voice has no markdown and no
# URLs because a voice agent reads them out character by character.
LIMITS: dict[str, int] = {"voice": 700, "sms": 320, "chat": 1500, "document": 4000}
NO_MARKDOWN = {"voice", "sms"}
NO_URLS = {"voice", "sms"}

# ---------------------------------------------------------------------------
# 1. Redaction
# ---------------------------------------------------------------------------

# What each audience may be told about, by fact key. Anything not listed is dropped before Claude
# sees it. Add a key here only with a reason; this list is the privacy boundary.
ALLOWED: dict[str, set[str]] = {
    # The student may see everything we hold about her, because it is hers.
    "student": {
        "name", "visa", "arrival_date", "school", "employer", "calendar_year", "work_auth",
        "paystub_count", "period_first", "period_last", "ss", "medicare", "total", "amount",
        "rule", "quote", "source_title", "source_url", "case_state", "next_follow_up",
        "hours_over_limit", "hours_week", "deadline", "form", "document_title", "document_fields",
        "group_employer", "group_joined", "group_total", "group_invited",
        "research_topic", "research_sources", "promised_by", "reference_no", "refund_landed",
    },
    # Payroll is asked for one thing and told only what supports it. No hours (that is an
    # immigration matter and none of their business), no bank data, no arrival date, no other
    # findings, no other students.
    "payroll": {
        "name", "visa", "calendar_year", "employer", "paystub_count", "period_first", "period_last",
        "ss", "medicare", "total", "amount", "quote", "source_title", "promised_by", "reference_no",
    },
    # A group ask names the employer and the size of the problem, never an individual.
    "group": {
        "group_employer", "group_joined", "group_total", "rule", "quote", "source_title",
        "period_first", "period_last",
    },
    # Research prompts and anything that leaves for a third-party service: no personal facts at all.
    "public": {"visa", "rule", "research_topic", "employer_kind", "state"},
}

# Keys that must never appear in any rendered text, whatever the audience, because they identify a
# person or an account. They are stripped from the facts and then checked for in the output.
NEVER_RENDER = {"phone", "phone_masked", "nessie_id", "account_id", "ssn", "itin", "student_address",
                "transaction_id", "bank_balance", "home_address", "email"}


def redact(facts: dict, audience: Audience) -> dict:
    """The slice of `facts` this audience is allowed to be told about."""
    allowed = ALLOWED[audience]
    return {k: v for k, v in facts.items() if k in allowed and k not in NEVER_RENDER and v is not None}


def dropped(facts: dict, audience: Audience) -> list[str]:
    """Fact keys withheld from this audience, so the activity log can say what was not sent."""
    allowed = ALLOWED[audience]
    return sorted(k for k, v in facts.items() if v is not None and (k not in allowed or k in NEVER_RENDER))


# ---------------------------------------------------------------------------
# 2. Conversion
# ---------------------------------------------------------------------------

SYSTEM = """You are the writing layer of Docket, an assistant that helps F-1 international students
recover payroll tax withheld in error. You turn facts that have already been computed into words.

WHAT YOU ARE GIVEN
- An audience, a channel and a purpose.
- Facts. Every number in them was computed by our rules engine from stored records.
- Sometimes verified source excerpts, which our code has already matched word for word against the
  stored official text.

HARD RULES
1. Never do arithmetic and never state a number that is not in the facts, including dates and counts.
2. Only quote text that appears in the provided excerpts, word for word. If nothing supports a point,
   leave the point out.
3. Never invent a tax rule, form number, deadline, phone number, person or organisation.
4. Say only what the facts contain. Do not guess at anything missing, and do not fill a gap with a
   typical case. If something important is missing, say what is missing and who to ask.
5. Never add a disclaimer, an approval request or a sign-off; our code adds those.
6. You are writing for exactly one audience. Do not mention facts about anyone else.

CHANNELS
- voice: it will be read aloud by a voice agent. One or two short sentences. No markdown, no URLs,
  no bullet lists, no symbols that do not read aloud. Write amounts as "440 dollars and 64 cents".
  Do not quote the regulation: say what it means in your own words.
- sms: under 300 characters. Plain text, no markdown, no URLs. Do not quote the regulation.
- chat: plain words, 6th-grade reading level, under 120 words. Light markdown is fine.
- document: formal and complete, suitable for an employer or a tax authority to read.

TONE
Plain, calm and specific. The reader is a student who may be worried about money and about their
visa status. Never alarm them, never promise an outcome, and never imply that Docket is a lawyer or
a tax advisor."""


@dataclass
class Rendered:
    text: str
    channel: str
    audience: str
    checked: bool                      # True when Claude's text passed; False when the fallback was used
    problems: list[str] = field(default_factory=list)
    withheld: list[str] = field(default_factory=list)


_client = None


def _anthropic():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    return _client


def write(purpose: str, facts: dict, channel: Channel, audience: Audience,
          excerpts: dict[str, str] | None = None) -> str:
    """Claude's words for one purpose, audience and channel. Raises on an API failure."""
    content = (
        f"Audience: {audience}\nChannel: {channel}\nPurpose: {purpose}\n\n"
        f"Facts:\n<facts>\n{json.dumps(facts, indent=2, default=str)}\n</facts>"
    )
    if excerpts:
        content += f"\n\nVerified source excerpts:\n<excerpts>\n{json.dumps(excerpts, indent=2)}\n</excerpts>"
    content += f"\n\nWrite the {channel} message now. Output only the message text."
    response = _anthropic().messages.create(
        model=MODEL,
        # Thinking is on by default on this model and counts against max_tokens, so leave headroom
        # even though the message itself is a few sentences. Low effort: this is phrasing, not
        # reasoning, and it is on the path of a live call.
        max_tokens=8000,
        output_config={"effort": "low"},
        system=SYSTEM,
        messages=[{"role": "user", "content": content}],
    )
    parts = [b.text for b in response.content if getattr(b, "type", "") == "text"]
    text = "".join(parts).strip()
    if not text:
        raise RuntimeError(f"the writing layer returned nothing (stop_reason={response.stop_reason})")
    return text


# ---------------------------------------------------------------------------
# 3. Checks on what came back
# ---------------------------------------------------------------------------

_MONEY = re.compile(r"\$\s?([\d,]+(?:\.\d{2})?)")
_SPOKEN_MONEY = re.compile(r"\b([\d,]+)\s+dollars?(?:\s+and\s+(\d{1,2})\s+cents?)?", re.I)
_QUOTED = re.compile(r"[\"“]([^\"”]{20,})[\"”]")
_PHONE = re.compile(r"(?:\+\d[\d\-\s().]{7,}\d)|(?:\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b)")
_URL = re.compile(r"https?://|www\.", re.I)
_MARKDOWN = re.compile(r"\*\*|^[-*]\s|^#{1,6}\s|\[[^\]]+\]\([^)]+\)", re.M)


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def allowed_amounts(facts: dict) -> set[str]:
    """Every money-looking value in the facts, normalised to digits only, in both forms Claude may
    use: "$440.64" and "440 dollars and 64 cents"."""
    out: set[str] = set()

    def walk(value):
        if isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, (list, tuple)):
            for v in value:
                walk(v)
        elif isinstance(value, str):
            for m in _MONEY.finditer(value):
                out.add(_digits(m.group(1)) if "." in m.group(1) else _digits(m.group(1)) + "00")
            for m in _SPOKEN_MONEY.finditer(value):
                out.add(_digits(m.group(1)) + (m.group(2) or "0").zfill(2))
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            out.add(_digits(f"{value:.2f}"))
    walk(facts)
    return out


def allowed_phone_digits(facts: dict) -> set[str]:
    """Numbers we supplied, so a number Claude produced from memory can be told apart."""
    out: set[str] = set()

    def walk(value):
        if isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, (list, tuple)):
            for v in value:
                walk(v)
        elif isinstance(value, str):
            for m in _PHONE.finditer(value):
                out.add(_digits(m.group(0))[-10:])
    walk(facts)
    return out


def problems(text: str, facts: dict, channel: Channel, audience: Audience,
             sources: dict[str, str] | None = None, withheld: list[str] | None = None) -> list[str]:
    """Why this text cannot be sent. Empty when it passes."""
    found: list[str] = []
    limit = LIMITS[channel]
    if len(text) > limit:
        found.append(f"{len(text)} characters is over the {channel} limit of {limit}")
    if not text.strip():
        found.append("empty message")

    amounts = allowed_amounts(facts)
    for m in _MONEY.finditer(text):
        value = _digits(m.group(1)) if "." in m.group(1) else _digits(m.group(1)) + "00"
        if value not in amounts:
            found.append(f"amount ${m.group(1)} is not in the facts")
    for m in _SPOKEN_MONEY.finditer(text):
        value = _digits(m.group(1)) + (m.group(2) or "0").zfill(2)
        if value not in amounts:
            found.append(f"spoken amount {m.group(0)!r} is not in the facts")

    # A quote is allowed when it is word for word in a verified source, or when it is one of the
    # quotes we handed over in the facts (the rules engine already checked those against the stored
    # source before they got here). Anything else is text the model produced and is rejected.
    supplied = [v for k, v in facts.items() if k == "quote" and isinstance(v, str)]
    for m in _QUOTED.finditer(text):
        quote = m.group(1)
        if len(quote.split()) < 8:
            continue
        if any(check_quote(quote, t).ok for t in (sources or {}).values()):
            continue
        if any(check_quote(quote, s).ok for s in supplied):
            continue
        found.append("quoted text is not word for word in a verified source")

    phones = allowed_phone_digits(facts)
    for m in _PHONE.finditer(text):
        if _digits(m.group(0))[-10:] not in phones:
            found.append("a phone number appears that we did not supply")

    if channel in NO_MARKDOWN and _MARKDOWN.search(text):
        found.append(f"{channel} text must not contain markdown")
    if channel in NO_URLS and _URL.search(text):
        found.append(f"{channel} text must not contain a URL")

    # A fact withheld from this audience must not reappear in the words.
    for key in withheld or []:
        value = facts.get(key)
        if isinstance(value, str) and len(value) > 3 and value.lower() in text.lower():
            found.append(f"withheld fact {key!r} appears in the text")
    return found


# ---------------------------------------------------------------------------
# The one call the agents make
# ---------------------------------------------------------------------------

def speak(purpose: str, facts: dict, channel: Channel, audience: Audience, fallback: str,
          excerpts: dict[str, str] | None = None, sources: dict[str, str] | None = None,
          log_fn=None, agent: str = "guard") -> Rendered:
    """Render one message safely.

    `fallback` is a sentence written in code that is already correct for this audience and channel;
    it is what gets sent if Claude is unreachable or writes something that fails a check. Callers
    always have one, so this function never returns nothing.
    """
    allowed = redact(facts, audience)
    withheld = dropped(facts, audience)
    # A spoken or texted message is the wrong place for a verbatim regulation: there is no room for
    # it and no way to show the source beside it. The student sees the clause in chat and on the
    # dashboard, where it can sit next to the page it came from.
    if channel in {"voice", "sms"}:
        allowed = {k: v for k, v in allowed.items() if k not in {"quote", "source_url"}}

    def record(action: str, detail: str) -> None:
        if log_fn is None:
            return
        try:
            log_fn(agent, action, detail[:300])
        except Exception:  # noqa: BLE001 - a logging failure never blocks a message
            pass

    try:
        text = write(purpose, allowed, channel, audience, excerpts)
    except Exception as e:  # noqa: BLE001 - the fallback is always safe to send
        record("render_failed", f"{purpose} for {audience} on {channel}: {type(e).__name__}: {e}")
        return Rendered(fallback, channel, audience, checked=False,
                        problems=[f"writing layer unavailable: {e}"], withheld=withheld)

    found = problems(text, allowed, channel, audience, sources, withheld)
    if found:
        record("render_rejected", f"{purpose} for {audience} on {channel}: {'; '.join(found)}")
        return Rendered(fallback, channel, audience, checked=False, problems=found, withheld=withheld)

    record("render_checked",
           f"{purpose} for {audience} on {channel}: amounts, quotes and numbers verified"
           + (f"; withheld {', '.join(withheld)}" if withheld else ""))
    return Rendered(text, channel, audience, checked=True, withheld=withheld)


def for_voice(text: str) -> str:
    """Last pass before a voice agent reads a code-written sentence: strip what does not read aloud."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"https?://\S+", "our website", text)
    text = re.sub(r"\$(\d[\d,]*)\.(\d{2})",
                  lambda m: f"{m.group(1).replace(',', '')} dollars and {int(m.group(2))} cents", text)
    text = re.sub(r"\$(\d[\d,]*)", lambda m: f"{m.group(1).replace(',', '')} dollars", text)
    return re.sub(r"\s+", " ", text).strip()


def for_sms(text: str, limit: int = LIMITS["sms"]) -> str:
    """Code-written text trimmed to one text message, cut at a sentence where possible."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    stop = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return (cut[: stop + 1] if stop > limit * 0.6 else cut.rstrip()) + "…"
