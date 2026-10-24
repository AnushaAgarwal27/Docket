"""Download each rule's official page to sources/<source_id>.txt, so quotes can be checked
against the page itself without Convex.

    python -m rules.download_sources
    python -m rules.verify_sources

Text extraction matches seed/fetch_sources.py, so both copies of a page compare the same way.
"""
import hashlib
import html
import re
import sys

import requests

from rules.engine import SOURCES_DIR, load_rules
from rules.quote_checker import source_status

HEADERS = {"User-Agent": "Mozilla/5.0 (Docket source collector; Cal Hacks 13.0)"}


def page_text(raw_html: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw_html)
    text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def main() -> int:
    SOURCES_DIR.mkdir(exist_ok=True)
    failed = 0
    for rule in load_rules():
        url = rule.get("fetch_url", rule["source_url"])
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"FAIL     {rule['id']}: {e}")
            failed += 1
            continue
        text = page_text(resp.text)
        (SOURCES_DIR / f"{rule['source_id']}.txt").write_text(text)
        digest = hashlib.sha256(text.encode()).hexdigest()[:12]
        print(f"SAVED    {rule['id']}: {len(text):,} chars, sha256 {digest}, {source_status(rule['source_url'])} source")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
