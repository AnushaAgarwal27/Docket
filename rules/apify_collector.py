"""Fetch the official source pages through Apify's Website Content Crawler.

One Actor run fetches every rule's page (depth 0, plain HTTP crawler, raw HTML kept). The HTML
goes through the same `page_text()` as the plain fetcher, so a quote verified on one copy
matches the other. Needs APIFY_TOKEN.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlparse

import requests

from rules.download_sources import HEADERS, page_text

ACTOR = "apify/website-content-crawler"


@dataclass(frozen=True)
class Page:
    rule_id: str
    url: str  # the rule's public source_url, which is what the sources table is keyed on
    text: str
    hash: str
    run_id: str  # "http-fallback" when Apify returned no text and the page was fetched directly


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


def same_page(wanted: str, got: str) -> bool:
    """True when `got` is `wanted` after a redirect that only added query parameters
    (eCFR adds chapter, subchapter and subpart to the section URL)."""
    w, g = urlparse(wanted), urlparse(got)
    return (w.netloc, w.path.rstrip("/")) == (g.netloc, g.path.rstrip("/")) and \
        set(parse_qsl(w.query)) <= set(parse_qsl(g.query))


def _http_text(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
    except requests.RequestException:
        return ""
    return page_text(resp.text)


def collect(rules: list[dict], client=None, fallback=_http_text) -> tuple[list[Page], list[str]]:
    """Returns the fetched pages and the ids of rules whose page couldn't be fetched at all.
    A page Apify returns empty is fetched directly instead, marked run_id "http-fallback"."""
    if client is None:
        from apify_client import ApifyClient
        client = ApifyClient(os.environ["APIFY_TOKEN"])
    fetch = {r["id"]: r.get("fetch_url", r["source_url"]) for r in rules}
    run = client.actor(ACTOR).call(run_input=run_input(sorted(set(fetch.values()))))
    if run is None or run.get("status") != "SUCCEEDED":
        raise RuntimeError(f"Apify run did not succeed: {None if run is None else run.get('status')}")
    crawled = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        body = page_text(item["html"]) if item.get("html") else item.get("text") or ""
        urls = {item.get("url"), (item.get("crawl") or {}).get("loadedUrl")} - {None}
        crawled.append((urls, body))
    pages, missing = [], []
    for rule in rules:
        text = next((body for urls, body in crawled if body and any(same_page(fetch[rule["id"]], u) for u in urls)), "")
        run_id = run["id"]
        if not text and fallback:
            text, run_id = fallback(fetch[rule["id"]]), "http-fallback"
        if not text:
            missing.append(rule["id"])
            continue
        pages.append(Page(rule["id"], rule["source_url"], text, hashlib.sha256(text.encode()).hexdigest(), run_id))
    return pages, missing
