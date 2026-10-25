"""Fetch the official source pages through Apify.

One Website Content Crawler run fetches every rule's page (depth 0, plain HTTP crawler, raw HTML
kept). It skips pages it finds no readable text in, such as the eCFR renderer's bare HTML
fragment, so those go through a second run of Apify's Cheerio Scraper, which returns the raw
response body. Only a page both miss is fetched directly. Every HTML copy goes through the same
`page_text()` as the plain fetcher, so a quote verified on one copy matches the other.
Needs APIFY_TOKEN.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlparse

import requests

from rules.download_sources import HEADERS, page_text

ACTOR = "apify/website-content-crawler"
RAW_ACTOR = "apify/cheerio-scraper"
RAW_PAGE_FUNCTION = """async function pageFunction(context) {
    const { request, body } = context;
    return { url: request.url, loadedUrl: request.loadedUrl, html: body.toString() };
}"""
VIA = {ACTOR: "Website Content Crawler", RAW_ACTOR: "Cheerio Scraper"}


@dataclass(frozen=True)
class Page:
    rule_id: str
    url: str  # the rule's public source_url, which is what the sources table is keyed on
    text: str
    hash: str
    run_id: str  # "http-fallback" when both Apify runs returned no text and the page was fetched directly
    via: str = "Website Content Crawler"


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


def raw_input(urls: list[str]) -> dict:
    return {
        "startUrls": [{"url": u} for u in urls],
        "pageFunction": RAW_PAGE_FUNCTION,
        "maxCrawlingDepth": 0,
        "maxRequestsPerCrawl": len(urls),
        "proxyConfiguration": {"useApifyProxy": True},
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


def _run(client, actor: str, body: dict) -> tuple[str, list[tuple[set[str], str]]]:
    run = client.actor(actor).call(run_input=body)
    if run is None or run.get("status") != "SUCCEEDED":
        raise RuntimeError(f"Apify {actor} run did not succeed: {None if run is None else run.get('status')}")
    crawled = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        text = page_text(item["html"]) if item.get("html") else item.get("text") or ""
        urls = {item.get("url"), item.get("loadedUrl"), (item.get("crawl") or {}).get("loadedUrl")} - {None}
        crawled.append((urls, text))
    return run["id"], crawled


def _match(url: str, crawled: list[tuple[set[str], str]]) -> str:
    return next((text for urls, text in crawled if text and any(same_page(url, u) for u in urls)), "")


def collect(rules: list[dict], client=None, fallback=_http_text) -> tuple[list[Page], list[str]]:
    """Returns the fetched pages and the ids of rules whose page couldn't be fetched at all."""
    if client is None:
        from apify_client import ApifyClient
        client = ApifyClient(os.environ["APIFY_TOKEN"])
    fetch = {r["id"]: r.get("fetch_url", r["source_url"]) for r in rules}
    found: dict[str, tuple[str, str, str]] = {}  # rule id -> (text, run id, via)
    run_id, crawled = _run(client, ACTOR, run_input(sorted(set(fetch.values()))))
    for rule_id, url in fetch.items():
        if text := _match(url, crawled):
            found[rule_id] = (text, run_id, VIA[ACTOR])
    left = sorted({fetch[r] for r in fetch if r not in found})
    if left:
        try:
            run_id, crawled = _run(client, RAW_ACTOR, raw_input(left))
        except Exception as e:  # e.g. the Actor's permissions not yet approved in Apify Console
            print(f"WARN     {VIA[RAW_ACTOR]} run failed, fetching {len(left)} page(s) directly: {e}")
            crawled = []
        for rule_id, url in fetch.items():
            if rule_id not in found and (text := _match(url, crawled)):
                found[rule_id] = (text, run_id, VIA[RAW_ACTOR])
    pages, missing = [], []
    for rule in rules:
        text, run_id, via = found.get(rule["id"], ("", "", ""))
        if not text and fallback:
            text, run_id, via = fallback(fetch[rule["id"]]), "http-fallback", "direct HTTP"
        if not text:
            missing.append(rule["id"])
            continue
        pages.append(Page(rule["id"], rule["source_url"], text, hashlib.sha256(text.encode()).hexdigest(), run_id, via))
    return pages, missing
