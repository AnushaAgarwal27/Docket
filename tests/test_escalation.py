"""Written request after a stall or refusal, and the rehearsal stand-in for payroll."""
from datetime import date

from agents.caseworker import rehearsal
from agents.caseworker.engine import draft_written_request
from seed import demo_data

CASE = {"_id": "c1", "amountCents": 44064, "nextFollowUp": "2026-10-27"}
FLAG = {"quote": "Social security and Medicare taxes are not withheld from pay for the work unless the student is considered a resident alien."}


def letter():
    stubs = demo_data.paystubs()
    return draft_written_request(CASE, demo_data.PROFILE, stubs, FLAG, "IRS Publication 519", today=date(2026, 10, 24))


def test_letter_has_the_facts_and_the_two_asks():
    text = letter()
    assert "October 24, 2026" in text and "November 3, 2026" in text  # reply-by is 10 days out
    assert "$357.12" in text and "$83.52" in text and "$440.64" in text
    assert "calendar year 3 of 5" in text
    assert FLAG["quote"] in text and "IRS Publication 519 states" in text
    assert "Form 843 and Form 8316" in text
    assert "follow up by phone on 2026-10-27" in text


def test_letter_shares_nothing_payroll_does_not_need():
    text = letter().lower()
    for private in ("hour", "24 h", "20-hour", "visa history", "bank", "deposit", "inr", "pune"):
        assert private not in text, private


def test_rehearsal_outcomes_follow_the_setting_once():
    assert rehearsal.outcome_for({"payrollScript": "stall_once", "callAttempts": 1}) == "stalled"
    assert rehearsal.outcome_for({"payrollScript": "refuse_once", "callAttempts": 1}) == "refused"
    assert rehearsal.outcome_for({"payrollScript": "cooperate", "callAttempts": 1}) == "promised"
    assert rehearsal.outcome_for({"callAttempts": 1}) == "promised"
    assert rehearsal.outcome_for({"payrollScript": "stall_once", "callAttempts": 2}) == "promised"


def test_site_url(monkeypatch):
    monkeypatch.delenv("CONVEX_SITE_URL", raising=False)
    monkeypatch.setenv("CONVEX_URL", "https://basic-magpie-317.convex.cloud")
    assert rehearsal.site_url() == "https://basic-magpie-317.convex.site"
    monkeypatch.setenv("CONVEX_URL", "http://127.0.0.1:3210")
    assert rehearsal.site_url() == "http://127.0.0.1:3211"
    monkeypatch.setenv("CONVEX_SITE_URL", "https://example.convex.site/")
    assert rehearsal.site_url() == "https://example.convex.site"
