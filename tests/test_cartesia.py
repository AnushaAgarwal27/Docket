"""The Cartesia call starter, against a fake HTTP session (no network, no key)."""
import pytest

from agents.caseworker import cartesia

CASE = {"_id": "case123", "amountCents": 44064, "profileId": "p1"}
PROFILE = {"name": "Priya Sharma"}
STUBS = [{"employer": "University Dining Services"}] * 8
ENV = {
    "CARTESIA_API_KEY": "sk_car_test",
    "CARTESIA_AGENT_ID": "agent_1",
    "CARTESIA_FROM_NUMBER_ID": "num_1",
    "PAYROLL_PHONE": "+1 415-555-0123",
}


class Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body
        self.text = str(body)

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, resp):
        self.resp, self.calls = resp, []

    def post(self, url, json, headers, timeout):
        self.calls.append({"url": url, "json": json, "headers": headers})
        return self.resp


@pytest.fixture
def env(monkeypatch):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("CARTESIA_API_BASE", raising=False)


def test_request_shape(env):
    s = FakeSession(Resp(200, {"calls": [{"number": "+14155550123", "agent_call_id": "call_9", "error": None}]}))
    assert cartesia.place_call(CASE, PROFILE, STUBS, session=s) == "call_9"
    sent = s.calls[0]
    assert sent["url"] == "https://api.cartesia.ai/agents/calls"
    assert sent["headers"]["X-API-Key"] == "sk_car_test" and sent["headers"]["Cartesia-Version"]
    body = sent["json"]
    assert body["agent_id"] == "agent_1" and body["from_number_id"] == "num_1"
    call = body["outbound_calls"][0]
    assert call["to_number"] == "+14155550123"  # spaces and dashes stripped
    assert call["dynamic_variables"] == {
        "case_id": "case123", "student_name": "Priya Sharma", "employer": "University Dining Services",
        "refund_amount": "$440.64", "paycheck_count": "8",
    }


def test_per_destination_error_is_raised(env):
    s = FakeSession(Resp(200, {"calls": [{"number": "+14155550123", "agent_call_id": None, "error": "busy"}]}))
    with pytest.raises(cartesia.CallError, match="busy"):
        cartesia.place_call(CASE, PROFILE, STUBS, session=s)


def test_http_error_is_raised(env):
    with pytest.raises(cartesia.CallError, match="404"):
        cartesia.place_call(CASE, PROFILE, STUBS, session=FakeSession(Resp(404, {"detail": "agent not found"})))


def test_missing_settings(monkeypatch):
    for k in ENV:
        monkeypatch.delenv(k, raising=False)
    assert cartesia.missing_settings() == list(cartesia.REQUIRED)
    with pytest.raises(cartesia.CallError, match="not configured"):
        cartesia.place_call(CASE, PROFILE, STUBS, session=FakeSession(None))


def test_bad_phone_number(env, monkeypatch):
    monkeypatch.setenv("PAYROLL_PHONE", "415 555 0123")
    with pytest.raises(cartesia.CallError, match="E.164"):
        cartesia.place_call(CASE, PROFILE, STUBS, session=FakeSession(None))
