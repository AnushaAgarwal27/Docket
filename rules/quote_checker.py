"""The guardrail: a flag is shown only if its quoted clause appears word for word in the stored source."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

MIN_QUOTE_WORDS = 8  # a two-word "quote" like "are exempt" would match almost anything

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
