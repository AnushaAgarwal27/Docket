from datetime import date

import agents.coordinator.season as season
from seed.demo_data import SCHOOL_CALENDAR, paystubs

TODAY = date(2026, 10, 24)
PRIYA = {"name": "Priya", "visa": "F-1", "arrivalDate": "2024-08-15", "filed8843Years": [2024, 2025],
         "filings": [{"year": 2024, "form": "8843"}, {"year": 2025, "form": "8843"}]}


def run(profile, monkeypatch):
    monkeypatch.setattr(season, "query", lambda name, args: None)  # no stored source: no quote shown
    return season.next_season(profile, paystubs(), SCHOOL_CALENDAR, TODAY)


def test_priya_year_three(monkeypatch):
    out = run(PRIYA, monkeypatch)
    assert "calendar year 3 of 5" in out and "through 2028" in out
    assert "Last year (2025) you filed: Form 8843." in out
    assert "Form 8843 for 2026" in out and "2027-04-15" in out and "US wages" in out


def test_last_exempt_year(monkeypatch):
    out = run({**PRIYA, "arrivalDate": "2022-08-15"}, monkeypatch)
    assert "calendar year 5 of 5" in out and "last exempt year" in out


def test_past_the_exemption_hands_off(monkeypatch):
    out = run({**PRIYA, "arrivalDate": "2020-08-15"}, monkeypatch)
    assert "calendar year 7" in out and "international student office" in out and "8843" not in out


def test_nothing_filed_last_year(monkeypatch):
    out = run({**PRIYA, "filed8843Years": [], "filings": []}, monkeypatch)
    assert "I don't see any forms filed for 2025" in out
