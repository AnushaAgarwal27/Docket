"""The "simulate 2 weeks" button's bank side: drop the $440.64 refund deposit into Priya's account.

    python -m seed.release_refund 2026-11-07
"""
import json
import sys

from dotenv import load_dotenv

from seed.reset import IDS_FILE
from seed.nessie import Nessie, release_refund

if __name__ == "__main__":
    load_dotenv()
    on_date = sys.argv[1]
    account = json.loads(IDS_FILE.read_text())["accountId"]
    print("Refund deposit", release_refund(Nessie(), account, on_date))
