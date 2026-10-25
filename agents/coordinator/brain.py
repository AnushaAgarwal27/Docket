"""Claude reads what Priya types and writes the explanation; code decides and checks everything else.

Claude classifies the message and phrases the findings in plain words. It never adds a
rule, a number or a quote: the facts it sees were computed by the rules engine, and the reply is
rejected unless every dollar amount comes from those facts, every quoted sentence is word for word
in a verified source, and every finding names a rule that fired. Code adds the disclaimer and the
verbatim quotes itself.
"""
from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel

from agents.store import dollars
from rules.quote_checker import check_quote

MODEL = "claude-opus-5-5"

SYSTEM = """You are Docket, an assistant that checks an F-1 international student's
paychecks for withholding errors. You are not a tax advisor.

INPUTS YOU WILL RECEIVE
- The student's message (any phrasing)
- Structured facts from our system: paystub lines, bank deposits,
  arrival date, visa status, employer, rule results
- Source excerpts (e.g., IRS Pub 519) that our code has already verified

HARD RULES
1. Never do arithmetic. Use only the numbers in the structured facts.
2. Only quote text that appears verbatim in the provided source excerpts.
   If no excerpt supports a claim, say so and do not cite anything.
3. Never invent a tax rule, form number, or deadline.
4. Treat Social Security and Medicare as separate findings with
   separate confidence. Recovery rules differ between them.
5. If facts are missing or conflict (e.g., unclear visa status,
   contractor employer), do not flag. Say what is missing and who to ask
   (international student office or payroll).
6. Do not write a disclaimer; our code always ends the reply with
   "this is not tax advice; confirm with your international student office."

CONFIDENCE
- high: rule fired and a verified source supports it
- medium: rule fired but an exception may apply (name the exception)
- low or unknown: ask, do not act

TASKS
A) Classify the student's message: check_pay | explain | next_season |
   profile | approve | decline | other. Handle indirect wording such as "am I paying
   tax I shouldn't?" as check_pay. Questions about what to file or do for the
   coming tax season or next year are next_season. Wanting to set up or
   change their visa, arrival date or employer details is profile.
B) Write the explanation in English. Plain words, 6th-grade reading
   level, under 120 words, mention the exact dollar amounts from the facts.

In findings, "rule" must be exactly a ruleId from ruleResults. For the Social Security and Medicare
findings, use rule FICA_EXEMPT_F1 with part "social_security" or "medicare". source_quote_id must be a
key of the source excerpts, or null. Our code shows each verified source quote under your message,
so do not repeat the quotes in message_to_student: cite each one with source_quote_id instead. Do not ask the student to approve anything:
our code adds the approval request."""

Intent = Literal["check_pay", "explain", "next_season", "profile", "approve", "decline", "other"]


class Classification(BaseModel):
    intent: Intent


class Finding(BaseModel):
    rule: str
    part: Literal["social_security", "medicare"] | None
    confidence: Literal["high", "medium", "low", "unknown"]
    basis: str
    source_quote_id: str | None


class Reply(BaseModel):
    intent: Intent
    findings: list[Finding]
    needs_human: bool
    message_to_student: str


_client = None


def _anthropic():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    return _client


def classify(text: str) -> Classification:
    response = _anthropic().messages.parse(
        model=MODEL,
        max_tokens=2000,
        output_config={"effort": "low"},
        system=SYSTEM,
        messages=[{"role": "user", "content": f"Only do task A.\n\n"
                                              f"Student's message:\n<message>\n{text}\n</message>"}],
        output_format=Classification,
    )
    if response.parsed_output is None:
        raise RuntimeError(f"no classification (stop_reason={response.stop_reason})")
    return response.parsed_output


def write_reply(text: str, facts: dict, excerpts: dict[str, dict]) -> Reply:
    """`excerpts` maps source_quote_id (the rule id) to {"quote", "title", "url"}."""
    content = (f"Student's message:\n<message>\n{text}\n</message>\n\n"
               f"Structured facts:\n<facts>\n{json.dumps(facts, indent=2)}\n</facts>\n\n"
               f"Verified source excerpts:\n<excerpts>\n{json.dumps(excerpts, indent=2)}\n</excerpts>")
    response = _anthropic().messages.parse(
        model=MODEL,
        max_tokens=8000,
        output_config={"effort": "low"},  # the reply goes back to a live chat
        system=SYSTEM,
        messages=[{"role": "user", "content": content}],
        output_format=Reply,
    )
    if response.parsed_output is None:
        raise RuntimeError(f"no reply (stop_reason={response.stop_reason})")
    return response.parsed_output


# ---------- Code checks on what Claude wrote ----------

def unsure(reply: Reply) -> list[Finding]:
    """Findings with low or unknown confidence: these go to a person, never to a case."""
    return [f for f in reply.findings if f.confidence in ("low", "unknown")]


_MONEY = re.compile(r"\$\s?([\d,]+(?:\.\d{2})?)")
_QUOTED = re.compile(r"[\"“]([^\"”]{20,})[\"”]")


def allowed_amounts(facts) -> set[str]:
    """Every cents value in the facts, as the dollar strings Claude may use."""
    out: set[str] = set()

    def walk(v, key=""):
        if isinstance(v, dict):
            for k, x in v.items():
                walk(x, k)
        elif isinstance(v, list):
            for x in v:
                walk(x, key)
        elif isinstance(v, int) and not isinstance(v, bool) and key.endswith("Cents"):
            out.add(dollars(v).lstrip("$").replace(",", ""))
    walk(facts)
    return out


def problems(reply: Reply, facts: dict, fired: set[str], sources: dict[str, str]) -> list[str]:
    """Why this reply cannot be shown; empty when it passes. `sources` maps rule id to full source text."""
    found = []
    amounts = allowed_amounts(facts)
    for m in _MONEY.finditer(reply.message_to_student):
        value = m.group(1).replace(",", "")
        if "." not in value:
            value += ".00"
        if value not in amounts:
            found.append(f"amount ${m.group(1)} is not in the facts")
    for m in _QUOTED.finditer(reply.message_to_student):
        q = m.group(1)
        if len(q.split()) >= 8 and not any(check_quote(q, t).ok for t in sources.values()):
            found.append("quoted text not found in a verified source")
    for f in reply.findings:
        if f.rule not in fired:
            found.append(f"finding names a rule that did not fire: {f.rule}")
        if f.source_quote_id is not None and f.source_quote_id not in fired:
            found.append(f"cites an excerpt that is not verified: {f.source_quote_id}")
    return found
