"""Thin Capital One Nessie client plus Priya's seed.

Endpoint shapes follow the public Nessie docs as we remember them; confirm against
https://api.nessieisreal.com/documentation before the first real run. Nessie takes dollars as
floats, so cents are converted only at this boundary.
"""
from __future__ import annotations

import os

import requests

from seed import demo_data

DEFAULT_BASE_URL = "https://api.nessieisreal.com"


def dollars(cents: int) -> float:
    return round(cents / 100, 2)


class Nessie:
    def __init__(self, key: str | None = None, base_url: str | None = None, session=None):
        self.key = key or os.environ["NESSIE_API_KEY"]
        # Read at call time, after load_dotenv(); plain http is refused on port 80.
        self.base = (base_url or os.environ.get("NESSIE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.http = session or requests.Session()

    def _call(self, method: str, path: str, body: dict | None = None):
        r = self.http.request(method, f"{self.base}{path}", params={"key": self.key}, json=body, timeout=20)
        r.raise_for_status()
        return r.json() if r.content else None

    def _create(self, path: str, body: dict) -> str:
        return self._call("POST", path, body)["objectCreated"]["_id"]

    def wipe(self) -> None:
        """Clears the demo data under this API key. Each team member should use their own key.

        Hackathon keys get 403 on the bulk /data delete, so on 403 fall back to deleting every
        account (which takes its deposits and purchases with it). Old customers and merchants
        stay behind; seed_priya always creates fresh ones, so they are harmless.
        """
        try:
            for kind in ("Deposits", "Purchases", "Accounts", "Merchants", "Customers"):
                self._call("DELETE", f"/data?type={kind}")
            return
        except requests.HTTPError as e:
            if e.response is None or e.response.status_code != 403:
                raise
        for account in self._call("GET", "/accounts") or []:
            try:
                self._call("DELETE", f"/accounts/{account['_id']}")
            except requests.HTTPError as e:
                print(f"Could not delete account {account['_id']}: {e}")

    def create_customer(self, first: str, last: str) -> str:
        return self._create("/customers", {
            "first_name": first, "last_name": last,
            "address": {"street_number": "2400", "street_name": "Durant Ave", "city": "Berkeley",
                        "state": "CA", "zip": "94704"},
        })

    def create_checking(self, customer_id: str, opening_cents: int) -> str:
        return self._create(f"/customers/{customer_id}/accounts", {
            "type": "Checking", "nickname": "Everyday checking", "rewards": 0,
            "balance": dollars(opening_cents),
        })

    def create_merchant(self, name: str, category: str) -> str:
        return self._create("/merchants", {"name": name, "category": category})

    def deposit(self, account_id: str, txn: dict) -> str:
        return self._create(f"/accounts/{account_id}/deposits", {
            "medium": "balance", "transaction_date": txn["date"], "status": "completed",
            "amount": dollars(txn["amountCents"]),
            "description": f"{txn['counterparty']} | {txn['memo']}",
        })

    def purchase(self, account_id: str, merchant_id: str, txn: dict) -> str:
        return self._create(f"/accounts/{account_id}/purchases", {
            "merchant_id": merchant_id, "medium": "balance", "purchase_date": txn["date"],
            "status": "completed", "amount": dollars(txn["amountCents"]),
            "description": f"{txn['counterparty']} | {txn['memo']}",
        })

    def list_deposits(self, account_id: str) -> list[dict]:
        return self._call("GET", f"/accounts/{account_id}/deposits") or []

    def list_purchases(self, account_id: str) -> list[dict]:
        return self._call("GET", f"/accounts/{account_id}/purchases") or []


OPENING_BALANCE_CENTS = 120000


def seed_priya(client: Nessie) -> dict:
    """Creates Priya's customer, account and every visible transaction. Returns the ids."""
    customer = client.create_customer("Priya", "Sharma")
    account = client.create_checking(customer, OPENING_BALANCE_CENTS)
    merchants: dict[str, str] = {}
    created = []
    for txn in demo_data.transactions():
        if txn["kind"] == "purchase":
            name = txn["counterparty"]
            if name not in merchants:
                merchants[name] = client.create_merchant(name, txn["memo"])
            created.append(client.purchase(account, merchants[name], txn))
        else:
            created.append(client.deposit(account, txn))
    return {"customerId": customer, "accountId": account, "transactionIds": created}


def release_refund(client: Nessie, account_id: str, on_date: str) -> str:
    """The "simulate 2 weeks" button: the employer's $440.64 FICA refund lands."""
    return client.deposit(account_id, {**demo_data.HIDDEN_REFUND, "date": on_date})
