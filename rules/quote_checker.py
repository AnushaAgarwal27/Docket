"""The guardrail: a flag is shown only if its quoted clause appears word for word in the stored source."""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlparse

MIN_QUOTE_WORDS = 8  # a two-word "quote" like "are exempt" would match almost anything

# Official domains a quote may come from. The school's own domains come from UNIVERSITY_DOMAINS
# (comma separated). A source anywhere else can still match, but it is marked unverified.
OFFICIAL_DOMAINS = ("irs.gov", "uscis.gov", "ecfr.gov")  # ecfr.gov: the official text of federal regulations
DEFAULT_UNIVERSITY_DOMAINS = "berkeley.edu"

_PUNCT = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", " ": " ",
})


def normalize(text: str) -> str:
    """NFKC, straight quotes and dashes, collapsed whitespace. Case and wording are untouched."""
    text = unicodedata.normalize("NFKC", text).translate(_PUNCT)
    return re.sub(r"\s+", " ", text).strip()


@dataclass(frozen=True)
class QuoteResult:
    ok: bool
    reason: str


def check_quote(quote: str, source_text: str) -> QuoteResult:
    q = normalize(quote).strip(' "')
    if len(q.split()) < MIN_QUOTE_WORDS:
        return QuoteResult(False, f"quote shorter than {MIN_QUOTE_WORDS} words")
    if q not in normalize(source_text):
        return QuoteResult(False, "quote not found in stored source")
    return QuoteResult(True, "exact match")


def allowed_domains() -> tuple[str, ...]:
    school = os.environ.get("UNIVERSITY_DOMAINS", DEFAULT_UNIVERSITY_DOMAINS)
    return OFFICIAL_DOMAINS + tuple(d.strip().lower() for d in school.split(",") if d.strip())


def source_status(url: str) -> str:
    """Returns "verified" when the source's host is an allowed domain or a subdomain of one."""
    host = (urlparse(url).hostname or "").lower()
    ok = any(host == d or host.endswith("." + d) for d in allowed_domains())
    return "verified" if ok else "unverified"
