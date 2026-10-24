"""Fetch the official source pages through Apify's Website Content Crawler.

One Actor run fetches every rule's page (depth 0, plain HTTP crawler, raw HTML kept). The HTML
goes through the same `page_text()` as the plain fetcher, so a quote verified on one copy
matches the other. Needs APIFY_TOKEN.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

from rules.download_sources import page_text

ACTOR = "apify/website-content-crawler"


@dataclass(frozen=True)
class Page:
    rule_id: str
    url: str  # the rule's public source_url, which is what the sources table is keyed on
    text: str
    hash: str
    run_id: str


def run_input(urls: list[str]) -> dict:
    return {
        "startUrls": [{"url": u} for u in urls],
        "crawlerType": "cheerio",  # plain HTTP: these pages need no browser
        "maxCrawlDepth": 0,
        "maxCrawlPages": len(urls),
        "useSitemaps": False,
        "saveHtml": True,
        "htmlTransformer": "none",
        "removeElementsCssSelector": "script, style, noscript",
    }


def collect(rules: list[dict], client=None) -> tuple[list[Page], list[str]]:
    """Returns the fetched pages and the ids of rules whose page didn't come back."""
    if client is None:
        from apify_client import ApifyClient
        client = ApifyClient(os.environ["APIFY_TOKEN"])
    fetch = {r["id"]: r.get("fetch_url", r["source_url"]) for r in rules}
    run = client.actor(ACTOR).call(run_input=run_input(sorted(set(fetch.values()))))
    if run is None or run.get("status") != "SUCCEEDED":
        raise RuntimeError(f"Apify run did not succeed: {None if run is None else run.get('status')}")
    by_url = {}
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        url = (item.get("crawl") or {}).get("loadedUrl") or item.get("url")
        body = page_text(item["html"]) if item.get("html") else item.get("text", "")
        for key in {url, item.get("url")}:
            if key:
                by_url[key.rstrip("/")] = body
    pages, missing = [], []
    for rule in rules:
        text = by_url.get(fetch[rule["id"]].rstrip("/"))
        if not text:
            missing.append(rule["id"])
            continue
        pages.append(Page(rule["id"], rule["source_url"], text, hashlib.sha256(text.encode()).hexdigest(), run["id"]))
    return pages, missing
