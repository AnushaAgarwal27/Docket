"""Fetch the official source pages named in rules.yaml into the sources table.

Stand-in for the Apify collector: same table, same fields. Run from the repo root:
    .venv/bin/python -m seed.fetch_sources
"""

import hashlib
import html
import re
from datetime import datetime, timezone

import requests
import yaml

from agents.store import log, mutation
from rules.quote_checker import check_quote

HEADERS = {"User-Agent": "Mozilla/5.0 (Docket source collector; Cal Hacks 13.0)"}


def page_text(raw_html: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw_html)
    text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw)).replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def main() -> None:
    rules = yaml.safe_load(open("rules/rules.yaml"))
    for rule in rules:
        resp = requests.get(rule.get("fetch_url", rule["source_url"]), headers=HEADERS, timeout=60)
        resp.raise_for_status()
        text = page_text(resp.text)
        source_id = mutation("sources:upsert", {
            "url": rule["source_url"],
            "title": rule["source_title"],
            "text": text,
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
            "hash": hashlib.sha256(text.encode()).hexdigest(),
        })
        ok = check_quote(rule["quote"], text).ok
        log("source-collector", "source_fetched",
            f"{rule['source_title']}: {len(text):,} chars; quote for {rule['id']} {'found' if ok else 'NOT FOUND'}",
            sourceId=source_id)
        print(f"{'OK ' if ok else 'BAD'} {rule['id']}: {len(text):,} chars from {rule['source_url']}")


if __name__ == "__main__":
    main()
