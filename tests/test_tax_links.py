from datetime import date

from agents.tax.engine import paystub_ids
from rules.rules import fica_exempt, over_20_hours_in_session
from seed.demo_data import PROFILE, SCHOOL_CALENDAR, paystubs

STUBS = [{**p, "_id": f"ps_{i}"} for i, p in enumerate(paystubs(), 1)]


def test_fica_links_every_paystub_it_counted():
    hit = fica_exempt(PROFILE, STUBS, SCHOOL_CALENDAR, date(2026, 10, 24))
    assert paystub_ids(hit, STUBS) == [f"ps_{i}" for i in range(1, 9)]


def test_hours_links_only_the_paystub_with_the_long_week():
    hit = over_20_hours_in_session(PROFILE, STUBS, SCHOOL_CALENDAR, date(2026, 10, 24))
    assert paystub_ids(hit, STUBS) == ["ps_5"]


def test_rule_without_paystubs_links_none():
    assert paystub_ids({"amountCents": 0, "taxYear": 2025}, STUBS) == []


def test_stored_profile_is_translated_for_the_rules():
    from agents.tax.engine import rules_profile
    stored = {**PROFILE, "employer": "University Dining Services", "employmentType": "employee", "employerIsSchool": True}
    assert rules_profile(stored)["employer"] == {"name": "University Dining Services", "type": "university"}
    assert rules_profile({**stored, "employmentType": "contractor"})["employer"]["type"] == "contractor"
    assert rules_profile({**stored, "employerIsSchool": False})["employer"] == {"name": "University Dining Services"}
    eval_style = {**PROFILE, "employer": {"name": "Residential Life", "type": "university"}}
    assert rules_profile(eval_style) is eval_style
    hit = fica_exempt(rules_profile(stored), STUBS, SCHOOL_CALENDAR, date(2026, 10, 24))
    assert hit["amountCents"] == 44064
