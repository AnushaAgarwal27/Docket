"""Quote checker: a clause is shown only if it appears word for word in the stored source."""

import re


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace(" ", " ")).strip()


def quote_in_source(quote: str, source_text: str) -> bool:
    q = normalize(quote)
    return bool(q) and q in normalize(source_text)
