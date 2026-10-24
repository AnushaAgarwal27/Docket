"""Rule checks. Each is a pure function of facts; code does all math, counting and decisions.

A check returns None (rule does not apply) or a dict with `amountCents` plus details the
explanation and the dashboard need. Dates are ISO strings, money is integer cents.
"""
from __future__ import annotations

from datetime import date, timedelta

STUDENT_VISAS_FICA = {"F-1"}
EXEMPT_INDIVIDUAL_VISAS = {"F-1", "J-1"}
EXEMPT_CALENDAR_YEARS = 5
WEEKLY_HOUR_LIMIT = 20


def calendar_year_number(arrival_date: str, year: int) -> int:
    """Which calendar year of US presence `year` is. Any part of a year counts as a full year,
    so arriving August 2024 makes 2024 year 1, 2025 year 2 and 2026 year 3."""
    return year - date.fromisoformat(arrival_date).year + 1


def _week_start(stub: dict, week_index: int) -> date:
    return date.fromisoformat(stub["periodStart"]) + timedelta(days=7 * week_index)


def _session_for(day: date, calendar: dict) -> dict | None:
    for s in calendar["sessions"]:
        if date.fromisoformat(s["start"]) <= day <= date.fromisoformat(s["end"]):
            return s
    return None


def fica_exempt(profile: dict, paystubs: list[dict], calendar: dict, as_of: date) -> dict | None:
    """F-1, within the first 5 calendar years, and Social Security or Medicare was withheld."""
    if profile["visa"] not in STUDENT_VISAS_FICA:
        return None
    hits = []
    for stub in paystubs:
        year = date.fromisoformat(stub["periodEnd"]).year
        n = calendar_year_number(profile["arrivalDate"], year)
        withheld = stub["ssCents"] + stub["medicareCents"]
        if n <= EXEMPT_CALENDAR_YEARS and withheld > 0:
            hits.append((stub, n, withheld))
    if not hits:
        return None
    return {
        "amountCents": sum(w for _, _, w in hits),
        "ssCents": sum(s["ssCents"] for s, _, _ in hits),
        "medicareCents": sum(s["medicareCents"] for s, _, _ in hits),
        "periods": [[s["periodStart"], s["periodEnd"]] for s, _, _ in hits],
        "calendarYears": sorted({n for _, n, _ in hits}),
        "employers": sorted({s["employer"] for s, _, _ in hits}),
    }


def over_20_hours_in_session(profile: dict, paystubs: list[dict], calendar: dict, as_of: date) -> dict | None:
    """Any week whose start date falls inside a session with hours above 20. Breaks are exempt."""
    weeks = []
    for stub in paystubs:
        for i, hours in enumerate(stub["hoursByWeek"]):
            start = _week_start(stub, i)
            session = _session_for(start, calendar)
            if hours > WEEKLY_HOUR_LIMIT and session:
                weeks.append({"weekStart": start.isoformat(), "hours": hours, "session": session["name"]})
    if not weeks:
        return None
    return {"amountCents": 0, "weeks": weeks}


def needs_8843(profile: dict, paystubs: list[dict], calendar: dict, as_of: date) -> dict | None:
    """F-1 or J-1, an exempt individual last tax year, and no 8843 recorded for it.

    Due April 15 when the student had US wages that year (filed with 1040-NR), otherwise June 15.
    Weekend/holiday shifts are not applied.
    """
    if profile["visa"] not in EXEMPT_INDIVIDUAL_VISAS:
        return None
    tax_year = as_of.year - 1
    n = calendar_year_number(profile["arrivalDate"], tax_year)
    if n < 1 or n > EXEMPT_CALENDAR_YEARS:
        return None
    if tax_year in profile.get("filed8843Years", []):
        return None
    had_wages = any(date.fromisoformat(s["periodEnd"]).year == tax_year and s["grossCents"] > 0 for s in paystubs)
    deadline = date(tax_year + 1, 4, 15) if had_wages else date(tax_year + 1, 6, 15)
    return {
        "amountCents": 0,
        "taxYear": tax_year,
        "deadline": deadline.isoformat(),
        "overdue": as_of > deadline,
        "hadWages": had_wages,
    }


CHECKS = {
    "fica_exempt": fica_exempt,
    "over_20_hours_in_session": over_20_hours_in_session,
    "needs_8843": needs_8843,
}
