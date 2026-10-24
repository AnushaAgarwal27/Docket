from datetime import date

from seed import demo_data as d
from rules.rules import calendar_year_number, fica_exempt, needs_8843, over_20_hours_in_session

AS_OF = date(2026, 10, 24)
CAL = d.SCHOOL_CALENDAR


def test_calendar_year_count():
    assert [calendar_year_number("2024-08-15", y) for y in (2024, 2025, 2026, 2028, 2029)] == [1, 2, 3, 5, 6]


def test_priya_fica_flag_is_hero_number():
    hit = fica_exempt(d.PROFILE, d.paystubs(), CAL, AS_OF)
    assert hit["amountCents"] == 44064 and hit["calendarYears"] == [3] and len(hit["periods"]) == 8


def test_sixth_calendar_year_not_exempt():
    profile = {**d.PROFILE, "arrivalDate": "2021-08-15"}  # 2026 is year 6
    assert fica_exempt(profile, d.paystubs(), CAL, AS_OF) is None


def test_nothing_withheld_no_flag():
    clean = [{**s, "ssCents": 0, "medicareCents": 0} for s in d.paystubs()]
    assert fica_exempt(d.PROFILE, clean, CAL, AS_OF) is None


def test_non_f1_not_flagged():
    assert fica_exempt({**d.PROFILE, "visa": "H-1B"}, d.paystubs(), CAL, AS_OF) is None


def test_priya_one_week_over_20():
    hit = over_20_hours_in_session(d.PROFILE, d.paystubs(), CAL, AS_OF)
    assert hit["weeks"] == [{"weekStart": "2026-03-16", "hours": 24, "session": "Spring 2026"}]


def test_over_20_during_winter_break_is_fine():
    stub = d.make_paystub(1, date(2025, 12, 22), [30, 30])
    assert over_20_hours_in_session(d.PROFILE, [stub], CAL, AS_OF) is None


def test_exactly_20_is_fine():
    stub = d.make_paystub(1, date(2026, 2, 2), [20, 20])
    assert over_20_hours_in_session(d.PROFILE, [stub], CAL, AS_OF) is None


def test_priya_already_filed_8843():
    assert needs_8843(d.PROFILE, d.paystubs(), CAL, AS_OF) is None


def test_no_income_still_needs_8843_due_june():
    profile = {**d.PROFILE, "filed8843Years": []}
    hit = needs_8843(profile, [], CAL, date(2026, 2, 1))
    assert hit == {"amountCents": 0, "taxYear": 2025, "deadline": "2026-06-15", "overdue": False, "hadWages": False}


def test_8843_with_wages_due_april():
    profile = {**d.PROFILE, "filed8843Years": []}
    stub = d.make_paystub(1, date(2025, 9, 1), [10, 10])
    assert needs_8843(profile, [stub], CAL, date(2026, 2, 1))["deadline"] == "2026-04-15"


def test_8843_not_required_after_exempt_years():
    profile = {**d.PROFILE, "arrivalDate": "2019-08-15", "filed8843Years": []}
    assert needs_8843(profile, [], CAL, date(2026, 2, 1)) is None
