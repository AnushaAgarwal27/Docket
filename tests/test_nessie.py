from seed import demo_data as d
from seed.nessie import Nessie, release_refund, seed_priya


class FakeResponse:
    def __init__(self, n):
        self.content = b"x"
        self._n = n

    def raise_for_status(self):
        pass

    def json(self):
        return {"objectCreated": {"_id": f"id{self._n}"}}


class FakeSession:
    def __init__(self):
        self.calls = []

    def request(self, method, url, params, json, timeout):
        self.calls.append((method, url, json))
        return FakeResponse(len(self.calls))


def test_seed_creates_everything_once_per_merchant():
    s = FakeSession()
    ids = seed_priya(Nessie("k", "http://nessie", s))
    paths = [u.removeprefix("http://nessie") for _, u, _ in s.calls]
    assert sum(p.endswith("/deposits") for p in paths) == 10  # 8 payroll + 2 family
    assert sum(p.endswith("/purchases") for p in paths) == 20
    assert sum(p == "/merchants" for p in paths) == len({p[1] for p in d.PURCHASES})
    assert len(ids["transactionIds"]) == 30


def test_amounts_sent_as_dollars_and_refund_is_hero_number():
    s = FakeSession()
    release_refund(Nessie("k", "http://nessie", s), "acct1", "2026-11-07")
    method, url, body = s.calls[0]
    assert url.endswith("/accounts/acct1/deposits") and body["amount"] == 440.64
    assert body["description"] == "University Dining Payroll | FICA refund"


class ForbiddenBulkSession(FakeSession):
    """Bulk /data delete is 403, like a hackathon key; per-account delete works."""

    def request(self, method, url, params, json, timeout):
        import requests
        self.calls.append((method, url, json))
        r = requests.Response()
        r.url = url
        if "/data" in url:
            r.status_code = 403
        elif method == "GET":
            r.status_code, r._content = 200, b'[{"_id": "a1"}, {"_id": "a2"}]'
        else:
            r.status_code, r._content = 202, b""
        return r


def test_wipe_falls_back_to_deleting_accounts_on_403():
    s = ForbiddenBulkSession()
    Nessie("k", "https://nessie", s).wipe()
    calls = [(m, u.removeprefix("https://nessie")) for m, u, _ in s.calls]
    assert calls == [("DELETE", "/data?type=Deposits"), ("GET", "/accounts"),
                     ("DELETE", "/accounts/a1"), ("DELETE", "/accounts/a2")]
