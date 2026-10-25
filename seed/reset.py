"""One command before every rehearsal: wipe Nessie and re-seed Priya.

    python -m seed.reset            # wipes Nessie too when NESSIE_API_KEY is set
    python -m seed.reset --dry-run  # print what would be created, no network

With DOCKET_DB_PATH set, it also runs seed:resetDemo with Priya's profile (keeping fetched sources), then
adds the simulated cohort for the employer pattern view (seed/cohort.py; skip with --no-cohort).
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


def student_profile() -> dict:
    """Priya's profile plus the employer, the forms she filed per year (from filed8843Years), and her job facts."""
    p = demo_data.PROFILE
    return {**p, "demo": True, "employer": demo_data.EMPLOYER,
            "filings": [{"year": y, "form": "8843"} for y in p.get("filed8843Years", [])],
            # facts the Hearing's objection checks read: on-campus employee of her own school, enrolled
            "employmentType": "employee", "employerIsSchool": True, "enrolled": True}


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-cohort", action="store_true", help="skip the simulated cohort for the employer pattern view")
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

    from agents.store import mutation
    profile_id = mutation("seed:resetDemo", {"profile": student_profile()})
    print(f"SQLite reset; Priya's profile id: {profile_id}")
    if not args.no_cohort:
        from seed.cohort import seed_cohort  # after Priya, so she stays the first profile
        print(f"Simulated cohort: {seed_cohort()}")


if __name__ == "__main__":
    main()
