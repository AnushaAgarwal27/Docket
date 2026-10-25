"""Download each rule's official page to sources/<source_id>.txt, so quotes can be checked
against the page itself without Convex.

    python -m rules.download_sources            # plain HTTP
    python -m rules.download_sources --apify    # through Apify (needs APIFY_TOKEN)
    python -m rules.verify_sources

The page's hash is kept in sources/<source_id>.sha256, so a re-run reports any page whose text
changed since the last download.

Text extraction matches seed/fetch_sources.py, so both copies of a page compare the same way.
"""
import argparse
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


def save(rule: dict, text: str, how: str) -> str:
    """Writes the page and its hash; returns NEW, SAME or CHANGED against the last download."""
    digest = hashlib.sha256(text.encode()).hexdigest()
    hash_file = SOURCES_DIR / f"{rule['source_id']}.sha256"
    before = hash_file.read_text().strip() if hash_file.exists() else None
    (SOURCES_DIR / f"{rule['source_id']}.txt").write_text(text)
    hash_file.write_text(digest + "\n")
    change = "NEW" if before is None else "SAME" if before == digest else "CHANGED"
    print(f"{change:<8} {rule['id']}: {len(text):,} chars via {how}, sha256 {digest[:12]}, "
          f"{source_status(rule['source_url'])} source")
    return change


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--apify", action="store_true", help="fetch through Apify's Website Content Crawler")
    args = ap.parse_args()
    SOURCES_DIR.mkdir(exist_ok=True)
    rules = load_rules()
    failed = 0
    if args.apify:
        from rules.apify_collector import collect
        pages, missing = collect(rules)
        by_id = {r["id"]: r for r in rules}
        for page in pages:
            how = "direct HTTP (Apify returned no text)" if page.run_id == "http-fallback" else \
                f"Apify {page.via} run {page.run_id}"
            save(by_id[page.rule_id], page.text, how)
        for rule_id in missing:
            print(f"FAIL     {rule_id}: page not in the Apify results")
        return 1 if missing else 0
    for rule in rules:
        url = rule.get("fetch_url", rule["source_url"])
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"FAIL     {rule['id']}: {e}")
            failed += 1
            continue
        save(rule, page_text(resp.text), "HTTP")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
