"""The demo redirect and the consent gate on calling the student.

The redirect is the thing standing between a research-found payroll number and someone's actual
phone ringing, so it gets tested as carefully as the money does.
"""
import pytest

from agents.voice import calls, student

ENV = {
    "CARTESIA_API_KEY": "sk_car_test",
    "CARTESIA_AGENT_ID": "agent_payroll",
    "CARTESIA_STUDENT_AGENT_ID": "agent_student",
    "CARTESIA_FROM_NUMBER_ID": "num_1",
}


class Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body
        self.text = str(body)

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, resp=None):
        self.resp = resp or Resp(200, {"calls": [{"agent_call_id": "call_1", "error": None}]})
        self.calls = []

    def post(self, url, json, headers, timeout):
        self.calls.append(json)
        return self.resp


@pytest.fixture
def env(monkeypatch):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    for k in ("CARTESIA_API_BASE", "DEMO_CALL_NUMBER", "DEMO_CALL_REDIRECT"):
        monkeypatch.delenv(k, raising=False)


# ---------- the redirect ----------

def test_redirect_is_on_unless_explicitly_turned_off(env, monkeypatch):
    assert calls.redirecting() is True
    monkeypatch.setenv("DEMO_CALL_REDIRECT", "1")
    assert calls.redirecting() is True
    monkeypatch.setenv("DEMO_CALL_REDIRECT", "0")
    assert calls.redirecting() is False


def test_only_the_demo_number_rings_while_the_redirect_is_on(env):
    dialled, intended = calls.destination("+14155550123")
    assert dialled == calls.DEFAULT_DEMO_NUMBER
    assert intended == "+14155550123"


def test_the_real_number_rings_once_the_redirect_is_off(env, monkeypatch):
    monkeypatch.setenv("DEMO_CALL_REDIRECT", "0")
    assert calls.destination("+1 415-555-0123") == ("+14155550123", "+14155550123")


def test_the_intended_number_travels_with_every_call(env):
    session = FakeSession()
    calls.place("+14155550123", {"case_id": "c1"}, session=session)
    variables = session.calls[0]["outbound_calls"][0]["dynamic_variables"]
    assert variables["intended_number"] == "+14155550123"
    assert session.calls[0]["outbound_calls"][0]["to_number"] == calls.DEFAULT_DEMO_NUMBER


def test_a_bad_number_is_refused_before_the_request_leaves(env):
    session = FakeSession()
    with pytest.raises(calls.CallError, match="E.164"):
        calls.place("415 555 0123 ext 4", {}, session=session)
    assert session.calls == []  # nothing was sent


def test_a_bad_demo_number_is_refused_too(env, monkeypatch):
    monkeypatch.setenv("DEMO_CALL_NUMBER", "not a number")
    with pytest.raises(calls.CallError, match="DEMO_CALL_NUMBER"):
        calls.destination("+14155550123")


def test_each_agent_has_its_own_configuration_check(env, monkeypatch):
    assert calls.missing_settings("CARTESIA_STUDENT_AGENT_ID") == []
    monkeypatch.delenv("CARTESIA_STUDENT_AGENT_ID")
    assert calls.missing_settings("CARTESIA_STUDENT_AGENT_ID") == ["CARTESIA_STUDENT_AGENT_ID"]
    assert calls.missing_settings("CARTESIA_AGENT_ID") == []  # the payroll agent is unaffected


def test_cartesia_errors_surface_as_call_errors(env):
    with pytest.raises(calls.CallError, match="403"):
        calls.place("+14155550123", {}, session=FakeSession(Resp(403, {"detail": "nope"})))
    busy = Resp(200, {"calls": [{"agent_call_id": None, "error": "busy"}]})
    with pytest.raises(calls.CallError, match="busy"):
        calls.place("+14155550123", {}, session=FakeSession(busy))


# ---------- the consent gate ----------

@pytest.mark.parametrize("profile,ok,reason", [
    ({"phone": "+14155550123", "voiceConsent": True}, True, ""),
    ({"phone": "+14155550123", "voiceConsent": False}, False, "turned on"),
    ({"phone": "+14155550123"}, False, "turned on"),
    ({"voiceConsent": True}, False, "no phone number"),
    ({"phone": "4155550123", "voiceConsent": True}, False, "E.164"),
])
def test_reachable(profile, ok, reason):
    reachable, why = student.reachable(profile)
    assert reachable is ok
    assert reason in why


def test_a_student_without_consent_is_not_called(env, monkeypatch):
    """The call is skipped and the reason is logged; it is never placed silently."""
    logged = []
    monkeypatch.setattr(student, "log", lambda *a, **k: logged.append(a))
    monkeypatch.setattr(student, "mutation", lambda *a, **k: pytest.fail("must not record a call"))
    result = student.call_student({"_id": "p1", "name": "Priya Sharma", "phone": "+14155550123"},
                                  "finding", "You have an issue.", session=FakeSession())
    assert result is None
    assert logged and logged[0][1] == "student_call_skipped"


def test_a_student_with_consent_is_called_on_the_student_agent(env, monkeypatch):
    recorded = {}
    monkeypatch.setattr(student, "log", lambda *a, **k: None)
    monkeypatch.setattr(student, "mutation", lambda name, args: recorded.update({name: args}))
    session = FakeSession()
    call_id = student.call_student(
        {"_id": "p1", "name": "Priya Sharma", "phone": "+14155550123", "voiceConsent": True},
        "finding", "Payroll withheld $440.64.", notification_id="n1", session=session)
    assert call_id == "call_1"
    assert session.calls[0]["agent_id"] == "agent_student"  # not the payroll agent
    variables = session.calls[0]["outbound_calls"][0]["dynamic_variables"]
    assert variables["student_name"] == "Priya"             # first name only
    assert "440 dollars and 64 cents" in variables["headline"]  # spoken, not "$440.64"
    assert recorded["calls:logStudentCall"]["toNumber"] == calls.DEFAULT_DEMO_NUMBER
