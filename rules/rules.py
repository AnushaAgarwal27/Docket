"""Rule checks. Each is a pure function of the profile and paystubs.

Code does all math, counting and decisions. Claude only explains.
Each check returns None when the rule does not fire, or a dict describing the hit.
"""

from datetime import date

FICA_EXEMPT_YEARS = 5
ONCAMPUS_WEEKLY_LIMIT = 20


def calendar_year_count(arrival_date: str, today: date) -> int:
    """Arrival in August 2024 makes 2024 year 1, so 2026 is year 3."""
    return today.year - date.fromisoformat(arrival_date).year + 1


def fica_exempt(profile: dict, paystubs: list[dict], today: date) -> dict | None:
    if profile["visa"] != "F-1":
        return None
    year = calendar_year_count(profile["arrivalDate"], today)
    if year > FICA_EXEMPT_YEARS:
        return None
    withheld = sum(p["ssCents"] + p["medicareCents"] for p in paystubs)
    if withheld == 0:
        return None
    return {"amountCents": withheld, "calendarYear": year}


def over_20_hours_in_session(profile: dict, paystubs: list[dict], today: date) -> dict | None:
    # TODO: skip weeks that fall in official school breaks (winter break eval case).
    for stub in paystubs:
        for i, hours in enumerate(stub["hoursByWeek"]):
            if hours > ONCAMPUS_WEEKLY_LIMIT:
                return {"amountCents": 0, "periodStart": stub["periodStart"], "week": i + 1, "hours": hours}
    return None


def needs_8843(profile: dict, paystubs: list[dict], today: date) -> dict | None:
    if profile["visa"] not in ("F-1", "J-1"):
        return None
    last_year = today.year - 1
    if last_year in profile.get("filed8843Years", []):
        return None
    # With US wages, 8843 goes in with the 1040-NR by April 15; with none, it is due June 15.
    deadline = f"{today.year}-04-15" if paystubs else f"{today.year}-06-15"
    return {"amountCents": 0, "taxYear": last_year, "deadline": deadline}
