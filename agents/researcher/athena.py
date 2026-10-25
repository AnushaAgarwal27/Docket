"""The research engines, and the rule that keeps their answers honest.

Two engines:

    ASI:One (api.asi1.ai)  Fetch.ai's deep-execution layer. The primary engine, and the one the
                           demo is about. Needs ASI_ONE_API_KEY and a model the account serves
                           (see ASI_MODEL below).

    Claude + web search    The fallback when ASI:One is unavailable or returns nothing. Its
                           sources come back as tool results, so they are real by construction.

Whichever answered, the answer then has to earn its sources:

    every URL in the answer is fetched by code. The page has to load, and it has to actually contain
    the claim's wording. A URL that does not load, or loads and does not support what was said, is
    dropped. An answer left with no surviving source is downgraded to low confidence and is never
    reported as fact, no matter how confident the engine sounded.

That check is the whole reason this is research rather than a model talking. It runs the same way on
both engines, in `verify_sources` below.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import requests

from rules.download_sources import HEADERS, page_text
from rules.quote_checker import normalize, source_status

ASI_BASE = "https://api.asi1.ai/v1"
# asi1 is the model our ASI:One account actually serves. "asi1-agentic" appears in Fetch's docs but
# 404s with model_not_found here, and a 404 is indistinguishable from any other failure at the call
# site: research silently fell back to Claude and still looked like it worked. Override with
# ASI_ONE_MODEL. `asi1-ultra` plans before it answers and needs a tool-call round trip this
# single-shot client does not do, so it returns "I'll search for..." and nothing else.
ASI_MODEL = os.environ.get("ASI_ONE_MODEL", "asi1")
CLAUDE_MODEL = "claude-opus-5"
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search"}

FETCH_TIMEOUT = 20
MAX_SOURCES = 6
# A claim counts as supported when a run of this many consecutive words from the answer appears on
# the page. Short enough to survive paraphrase, long enough that a chance match is unlikely.
SUPPORT_WINDOW = 6

URL_RE = re.compile(r"https?://[^\s<>\"'\)\]]+")

SYSTEM = """You are Docket's research agent. You research questions for F-1 international students
about pay, tax, work authorisation and immigration status in the United States.

Rules:
- Use official sources wherever one exists: irs.gov, uscis.gov, ecfr.gov, ice.gov/sevp, and the
  student's own university. Cite the exact page URL for every factual claim.
- Prefer the wording of the source. When you state a rule, quote the sentence that says it.
- Say plainly when something is unsettled, recently changed, or depends on facts you were not given.
- Never invent a URL, a form number, a dollar amount or a deadline.
- You are not a lawyer or a tax advisor and must not present yourself as one.
- Be brief. A few short paragraphs at most."""


@dataclass
class Source:
    title: str
    url: str
    excerpt: str = ""
    published_at: str | None = None
    verified: bool = False  # the page was fetched and supports the answer


@dataclass
class Finding:
    answer: str
    sources: list[Source] = field(default_factory=list)
    engine: str = "none"
    confidence: str = "low"
    error: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.answer.strip()) and not self.error


# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------

def asi_one_available() -> bool:
    return bool(os.environ.get("ASI_ONE_API_KEY"))


def ask_asi_one(question: str, context: str, session=requests) -> tuple[str, str]:
    """(answer, engine). Raises on an API failure so the caller can fall back."""
    key = os.environ["ASI_ONE_API_KEY"]
    base = os.environ.get("ASI_ONE_API_BASE", ASI_BASE).rstrip("/")
    body = {
        "model": ASI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"{context}\n\nResearch this and answer it:\n{question}"},
        ],
        "max_tokens": 2000,
        "stream": False,
    }
    resp = session.post(f"{base}/chat/completions", json=body, timeout=180,
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    if resp.status_code >= 400:
        raise RuntimeError(f"ASI:One returned {resp.status_code}: {resp.text[:300]}")
    choices = (resp.json() or {}).get("choices") or []
    if not choices:
        raise RuntimeError("ASI:One returned no choices")
    return (choices[0].get("message") or {}).get("content", "").strip(), ASI_MODEL


_client = None


def _anthropic():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    return _client


def ask_claude(question: str, context: str) -> tuple[str, list[Source], str]:
    """(answer, sources from the search tool, engine). Sources here come from tool results, so the
    URLs are ones the search actually returned rather than ones the model recalled."""
    response = _anthropic().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=16000,
        output_config={"effort": "medium"},
        system=SYSTEM,
        tools=[WEB_SEARCH_TOOL],
        messages=[{"role": "user", "content": f"{context}\n\nResearch this and answer it:\n{question}"}],
    )
    parts, sources = [], []
    for block in response.content:
        kind = getattr(block, "type", "")
        if kind == "text":
            parts.append(block.text)
        elif kind == "web_search_tool_result":
            results = getattr(block, "content", None)
            # An error comes back as a single object rather than a list of results.
            if isinstance(results, list):
                for r in results:
                    url, title = getattr(r, "url", ""), getattr(r, "title", "")
                    if url:
                        sources.append(Source(title=title or url, url=url,
                                              published_at=getattr(r, "page_age", None)))
    answer = "\n\n".join(p.strip() for p in parts if p.strip()).strip()
    if not answer:
        raise RuntimeError(f"Claude returned no text (stop_reason={response.stop_reason})")
    return answer, sources, CLAUDE_MODEL


# ---------------------------------------------------------------------------
# The source check
# ---------------------------------------------------------------------------

def fetch(url: str, session=requests) -> str:
    try:
        resp = session.get(url, headers=HEADERS, timeout=FETCH_TIMEOUT)
        resp.raise_for_status()
    except Exception:  # noqa: BLE001 - an unreachable source is simply not a source
        return ""
    return page_text(resp.text)


def supports(answer: str, page: str) -> str:
    """The longest run of the answer's own words found on the page, or "" if none is."""
    if not page:
        return ""
    haystack = normalize(page).lower()
    words = normalize(answer).split()
    best = ""
    for i in range(len(words) - SUPPORT_WINDOW + 1):
        window = " ".join(words[i:i + SUPPORT_WINDOW])
        if window.lower() in haystack and len(window) > len(best):
            best = window
    return best


def verify_sources(answer: str, candidates: list[Source], session=requests) -> list[Source]:
    """Fetch every candidate and keep the ones that load and support the answer.

    Candidates come from the engine; this is where they stop being claims. A page that 404s, times
    out, or loads but says nothing matching the answer is dropped here rather than shown.
    """
    seen, out = set(), []
    for source in candidates[:MAX_SOURCES]:
        url = source.url.rstrip(".,);")
        if url in seen:
            continue
        seen.add(url)
        excerpt = supports(answer, fetch(url, session=session))
        out.append(Source(title=source.title or url, url=url, excerpt=excerpt,
                          published_at=source.published_at, verified=bool(excerpt)))
    return out


def confidence_for(sources: list[Source]) -> str:
    """High only when an official page was fetched and found to support the answer."""
    verified = [s for s in sources if s.verified]
    if any(source_status(s.url) == "verified" for s in verified):
        return "high"
    if verified:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# What the rest of the agent calls
# ---------------------------------------------------------------------------

def research(question: str, context: str = "", session=requests) -> Finding:
    """Research one question. Never raises: a total failure comes back as a Finding with an error."""
    answer, sources, engine, error = "", [], "none", ""
    if asi_one_available():
        try:
            answer, engine = ask_asi_one(question, context, session=session)
            sources = [Source(title=u, url=u) for u in URL_RE.findall(answer)]
        except Exception as e:  # noqa: BLE001 - fall through to Claude
            error = f"ASI:One: {e}"
    if not answer:
        try:
            answer, sources, engine = ask_claude(question, context)
        except Exception as e:  # noqa: BLE001 - nothing left to try
            return Finding(answer="", engine=engine, error=f"{error}; Claude: {e}".lstrip("; "))
    checked = verify_sources(answer, sources, session=session)
    return Finding(answer=answer, sources=checked, engine=engine, confidence=confidence_for(checked))
