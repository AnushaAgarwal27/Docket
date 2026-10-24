"""One command before every rehearsal: wipe Nessie and re-seed Priya.

    python -m seed.reset            # needs NESSIE_API_KEY
    python -m seed.reset --dry-run  # print what would be created, no network

Convex is wiped by Person 3's reset mutation; set CONVEX_URL to call it from here too.
"""
import argparse
import json
import os
from pathlib import Path

from seed import demo_data
from seed.nessie import Nessie, seed_priya

IDS_FILE = Path(".nessie_ids.json")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    txns = demo_data.transactions()
    if args.dry_run:
        for t in txns:
            print(f"{t['date']}  {t['kind']:<12} {t['amountCents'] / 100:>9.2f}  {t['counterparty']}  ({t['memo']})")
        print(f"{len(txns)} transactions; hidden refund {demo_data.REFUND_CENTS / 100:.2f} held back")
        return

    client = Nessie()
    client.wipe()
    ids = seed_priya(client)
    IDS_FILE.write_text(json.dumps(ids, indent=2))
    print(f"Seeded Nessie: account {ids['accountId']}, {len(ids['transactionIds'])} transactions -> {IDS_FILE}")

    if os.environ.get("CONVEX_URL"):
        from convex import ConvexClient
        ConvexClient(os.environ["CONVEX_URL"]).mutation("admin:reset")
        print("Convex reset")


if __name__ == "__main__":
    main()
