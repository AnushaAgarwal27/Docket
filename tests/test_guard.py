"""The privacy boundary and the checks on what the writing layer produced.

Nothing here calls Claude: `guard.write` is the only part that does, and these tests are about the
redaction and the checks around it, which are the parts that have to hold when Claude is wrong.
"""
import pytest

from agents import guard

FACTS = {
    "name": "Priya Sharma",
    "visa": "F-1",
    "employer": "University Dining Services",
    "arrival_date": "2024-08-15",
    "total": "$440.64",
    "ss": "$357.12",
    "medicare": "$83.52",
    "paystub_count": 8,
    "hours_week": 24,
    "hours_over_limit": True,
    "phone": "+14155550123",
    "rule": "FICA_EXEMPT_F1",
    "quote": "Social security and Medicare taxes are not withheld from pay for the work",
    "source_title": "IRS Publication 519",
    "group_employer": "University Dining Services",
    "group_joined": 4,
}


# ---------- redaction ----------

def test_payroll_never_sees_hours_or_phone():
    """The 20-hour flag is an immigration matter and none of payroll's business; the phone number
    is hers. Neither is in payroll's allow-list, so there is nothing to leak."""
    allowed = guard.redact(FACTS, "payroll")
    assert "hours_week" not in allowed
    assert "hours_over_limit" not in allowed
    assert "phone" not in allowed
    assert "arrival_date" not in allowed
    # It does get what the refund request actually needs.
    assert allowed["total"] == "$440.64"
    assert allowed["name"] == "Priya Sharma"


def test_group_audience_cannot_carry_an_individual():
    """A group message names an employer and a count. There is no key in its allow-list that could
    carry a student's name or amount, so an individual cannot leak through it by mistake."""
    allowed = guard.redact(FACTS, "group")
    assert "name" not in allowed
    assert "total" not in allowed
    assert "ss" not in allowed
    assert allowed["group_employer"] == "University Dining Services"


def test_public_audience_has_no_personal_facts():
    """What leaves for a third-party research service."""
    allowed = guard.redact(FACTS, "public")
    assert set(allowed) <= {"visa", "rule", "research_topic", "employer_kind", "state"}
    assert "name" not in allowed and "employer" not in allowed


def test_never_render_keys_are_dropped_even_for_the_student():
    assert "phone" not in guard.redact(FACTS, "student")


def test_dropped_reports_what_was_withheld():
    withheld = guard.dropped(FACTS, "payroll")
    assert "hours_week" in withheld and "phone" in withheld


# ---------- checks on the rendered text ----------

def test_an_amount_not_in_the_facts_is_rejected():
    allowed = guard.redact(FACTS, "student")
    problems = guard.problems("You are owed $999.00.", allowed, "chat", "student")
    assert any("999" in p for p in problems)


def test_an_amount_from_the_facts_passes_in_both_forms():
    allowed = guard.redact(FACTS, "student")
    assert guard.problems("You are owed $440.64.", allowed, "chat", "student") == []
    assert guard.problems("You are owed 440 dollars and 64 cents.", allowed, "voice", "student") == []


def test_a_phone_number_we_did_not_supply_is_rejected():
    allowed = guard.redact(FACTS, "student")
    problems = guard.problems("Call payroll on 415-555-0199.", allowed, "chat", "student")
    assert any("phone number" in p for p in problems)


def test_a_quote_we_supplied_is_allowed_but_an_invented_one_is_not():
    allowed = guard.redact(FACTS, "student")
    assert guard.problems(f'The IRS says: "{FACTS["quote"]}"', allowed, "chat", "student") == []
    invented = 'The IRS says: "every student is entitled to a full refund within thirty days"'
    assert guard.problems(invented, allowed, "chat", "student") != []


def test_channel_limits_and_formatting():
    allowed = guard.redact(FACTS, "student")
    assert guard.problems("x" * 400, allowed, "sms", "student") != []          # too long for a text
    assert guard.problems("**bold**", allowed, "sms", "student") != []          # markdown does not send
    assert guard.problems("see https://irs.gov", allowed, "voice", "student") != []  # unreadable aloud
    assert guard.problems("**bold**", allowed, "chat", "student") == []         # fine in chat


def test_a_withheld_fact_reappearing_in_the_text_is_caught():
    """Belt and braces: the fact was never given to the writer, but if it turns up anyway the text
    does not go out."""
    allowed = guard.redact(FACTS, "payroll")
    withheld = guard.dropped(FACTS, "payroll")
    problems = guard.problems("She started on 2024-08-15.", FACTS, "document", "payroll",
                              withheld=withheld)
    assert any("arrival_date" in p for p in problems)


# ---------- the fallback path ----------

def test_speak_falls_back_when_the_writer_is_unavailable(monkeypatch):
    monkeypatch.setattr(guard, "write", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no key")))
    rendered = guard.speak("tell her", FACTS, "sms", "student", fallback="Payroll withheld $440.64.")
    assert rendered.text == "Payroll withheld $440.64."
    assert rendered.checked is False


def test_speak_falls_back_when_the_text_fails_a_check(monkeypatch):
    monkeypatch.setattr(guard, "write", lambda *a, **k: "You are owed $1,000,000.00.")
    rendered = guard.speak("tell her", FACTS, "chat", "student", fallback="Safe sentence.")
    assert rendered.text == "Safe sentence."
    assert rendered.checked is False
    assert rendered.problems


def test_speak_keeps_text_that_passes(monkeypatch):
    monkeypatch.setattr(guard, "write", lambda *a, **k: "Payroll withheld $440.64 you may be owed.")
    rendered = guard.speak("tell her", FACTS, "chat", "student", fallback="Safe sentence.")
    assert rendered.checked is True
    assert "440.64" in rendered.text


def test_voice_and_sms_never_get_the_quote(monkeypatch):
    """A spoken or texted message has no room for a regulation and no way to show its source
    beside it, so the quote is not even offered to the writer."""
    seen = {}
    monkeypatch.setattr(guard, "write",
                        lambda purpose, facts, channel, audience, excerpts=None: seen.setdefault(channel, facts) and "ok")
    guard.speak("p", FACTS, "voice", "student", fallback="f")
    guard.speak("p", FACTS, "chat", "student", fallback="f")
    assert "quote" not in seen["voice"]
    assert "quote" in seen["chat"]


# ---------- the code-written helpers ----------

@pytest.mark.parametrize("text,expected", [
    ("$440.64", "440 dollars and 64 cents"),
    ("$1,200.00", "1200 dollars and 0 cents"),
    ("**now**", "now"),
])
def test_for_voice_rewrites_what_cannot_be_read_aloud(text, expected):
    assert expected in guard.for_voice(text)


def test_for_voice_replaces_a_url():
    assert "http" not in guard.for_voice("see https://www.irs.gov/p519 for more")


def test_for_sms_trims_to_one_message():
    long = "First sentence here. " * 40
    out = guard.for_sms(long)
    assert len(out) <= guard.LIMITS["sms"]
    assert out.endswith("…") or out.endswith(".")
