"""One command before every rehearsal: wipe Nessie and re-seed Priya.

    python -m seed.reset            # wipes Nessie too when NESSIE_API_KEY is set
    python -m seed.reset --dry-run  # print what would be created, no network

With CONVEX_URL set, it also runs seed:resetDemo with Priya's profile, which keeps fetched sources.
Paystubs come from the Ledger reading seed/paystubs/*.pdf, not from this script.
"""
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from seed import demo_data
from seed.nessie import Nessie, seed_priya

IDS_FILE = Path(".nessie_ids.json")


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    txns = demo_data.transactions()
    if args.dry_run:
        for t in txns:
            print(f"{t['date']}  {t['kind']:<12} {t['amountCents'] / 100:>9.2f}  {t['counterparty']}  ({t['memo']})")
        print(f"{len(txns)} transactions; hidden refund {demo_data.REFUND_CENTS / 100:.2f} held back")
        return

    if os.environ.get("NESSIE_API_KEY"):
        client = Nessie()
        client.wipe()
        ids = seed_priya(client)
        IDS_FILE.write_text(json.dumps(ids, indent=2))
        print(f"Seeded Nessie: account {ids['accountId']}, {len(ids['transactionIds'])} transactions -> {IDS_FILE}")
    else:
        print("NESSIE_API_KEY not set; skipped the Nessie seed")

    if os.environ.get("CONVEX_URL"):
        from convex import ConvexClient
        profile_id = ConvexClient(os.environ["CONVEX_URL"]).mutation("seed:resetDemo", {"profile": demo_data.PROFILE})
        print(f"Convex reset; Priya's profile id: {profile_id}")


if __name__ == "__main__":
    main()
