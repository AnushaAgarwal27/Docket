"""The Apify source collector: fetch every rule's official page through Apify and store it in
the Convex `sources` table. Replaces the plain-HTTP stand-in, seed/fetch_sources.py.

    python -m seed.apify_sources      # needs APIFY_TOKEN and CONVEX_URL

Each page's hash is compared with the stored copy. A changed page logs `source_changed`, and
its rule's quote is checked again: if the quote no longer appears, the Tax agent's quote check
holds that rule's flags back until someone updates rules.yaml.
"""
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from rules.apify_collector import collect
from rules.engine import load_rules
from rules.quote_checker import check_quote

AGENT = "source-collector"


def sync(rules: list[dict], pages, convex) -> list[str]:
    """Stores each page and logs what happened; returns one printable line per rule."""
    by_id = {r["id"]: r for r in rules}
    lines = []
    for page in pages:
        rule = by_id[page.rule_id]
        before = convex.query("sources:getByUrl", {"url": page.url})
        source_id = convex.mutation("sources:upsert", {
            "url": page.url, "title": rule["source_title"], "text": page.text,
            "fetchedAt": datetime.now(timezone.utc).isoformat(), "hash": page.hash,
        })
        quote_ok = check_quote(rule["quote"], page.text).ok
        quote = "quote found" if quote_ok else "QUOTE NOT FOUND, flags held back"
        if before is not None and before["hash"] != page.hash:
            convex.mutation("activity:log", {
                "agent": AGENT, "action": "source_changed", "sourceId": source_id,
                "detail": f"{rule['source_title']} changed (sha256 {before['hash'][:12]} -> {page.hash[:12]}); "
                          f"{rule['id']} re-checked: {quote}",
            })
            status = "CHANGED"
        else:
            status = "NEW" if before is None else "SAME"
        convex.mutation("activity:log", {
            "agent": AGENT, "action": "source_fetched", "sourceId": source_id,
            "detail": f"{rule['source_title']}: {len(page.text):,} chars via "
                      f"{page.via if page.run_id == 'http-fallback' else f'Apify {page.via} run {page.run_id}'}; {quote}",
        })
        lines.append(f"{status:<8} {rule['id']}: {len(page.text):,} chars, {quote}")
    return lines


def main() -> None:
    load_dotenv()
    from convex import ConvexClient
    convex = ConvexClient(os.environ["CONVEX_URL"])
    rules = load_rules()
    pages, missing = collect(rules)
    for line in sync(rules, pages, convex):
        print(line)
    for rule_id in missing:
        convex.mutation("activity:log", {"agent": AGENT, "action": "source_fetch_failed",
                                         "detail": f"{rule_id}: page not in the Apify results"})
        print(f"FAIL     {rule_id}: page not in the Apify results")
    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
