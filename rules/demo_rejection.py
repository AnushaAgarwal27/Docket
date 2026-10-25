"""Show the quote checker rejecting a made-up clause, live on the dashboard feed.

    python -m rules.demo_rejection
    python -m rules.demo_rejection --clause "Any sentence a judge suggests"

Checks the clause against the stored IRS Pub 519 text (the FICA rule's source), then the
real rule quote, and logs both results to activity so the rejection shows in the feed.
"""
import argparse
import os

from dotenv import load_dotenv

from rules.engine import load_rules
from rules.quote_checker import check_quote

MADE_UP = "F-1 students are exempt from all federal taxes for their first five years in the United States."
RULE_ID = "FICA_EXEMPT_F1"


def demo_rows(clause: str, rule: dict, source: dict) -> list[dict]:
    """Activity rows for the made-up clause and the rule's real quote."""
    rows = []
    for label, quote in (("made-up clause", clause), ("stored rule quote", rule["quote"])):
        result = check_quote(quote, source["text"])
        rows.append({
            "agent": "tax",
            "action": "quote_accepted" if result.ok else "quote_rejected",
            "detail": f'{rule["id"]} ({label}): "{quote}" - {result.reason} in {source["title"]}',
            "sourceId": source["_id"],
        })
    return rows


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--clause", default=MADE_UP)
    args = ap.parse_args()

    from agents.store import client
    convex = client()
    rule = next(r for r in load_rules() if r["id"] == RULE_ID)
    source = convex.query("sources:getByUrl", {"url": rule["source_url"]})
    if source is None:
        raise SystemExit(f"No stored source for {rule['source_url']}; run python -m seed.fetch_sources first")
    for row in demo_rows(args.clause, rule, source):
        convex.mutation("activity:log", row)
        print(f"{'REJECTED' if row['action'] == 'quote_rejected' else 'ACCEPTED'}  {row['detail']}")


if __name__ == "__main__":
    main()
