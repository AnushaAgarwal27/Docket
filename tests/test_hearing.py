import json
from datetime import date
from pathlib import Path

import pytest

from agents.auditor.objections import objections
from agents.auditor.verdict import decide, verdict_line
from agents.tax import advocate
from rules.rules import fica_exempt
from seed.demo_data import PROFILE, SCHOOL_CALENDAR, paystubs

QUOTE_SOURCE = {"_id": "src_p519", "text": "Social security and Medicare taxes are not withheld from pay for the work "
                                           "unless the student is considered a resident alien."}
PRIYA = {**PROFILE, "_id": "p1", "employmentType": "employee", "employerIsSchool": True, "enrolled": True}


def stubs_with_ids(stubs):
    return [{**p, "_id": f"ps_{i}"} for i, p in enumerate(stubs, 1)]


def hearing(profile, stubs, as_of=date(2026, 10, 24)):
    hit = fica_exempt(profile, stubs, SCHOOL_CALENDAR, as_of)
    flag = {"_id": "flag_1"} if hit else None
    claim = advocate.fica_claim(profile, stubs, flag, hit, QUOTE_SOURCE)
    objs = objections(claim, profile)
    rebuttals = [advocate.rebut(o, claim, profile) for o in objs]
    return claim, objs, rebuttals, decide(claim, objs, rebuttals)


def test_priya_social_security_upheld_medicare_downgraded():
    claim, objs, rebuttals, v = hearing(PRIYA, stubs_with_ids(paystubs()))
    assert claim["amount_cents"] == 44064 and claim["calendar_years"] == [3] and claim["quote"]
    outcomes = {r["objection_id"]: r["outcome"] for r in rebuttals}
    assert outcomes == {"employer_is_contractor": "rebutted", "year_count_boundary": "rebutted",
                        "student_exception_applies": "rebutted", "medicare_recovery_uncertain": "conceded"}
    assert v["verdict"] == "downgraded" and v["parts"] == {"social_security": "upheld", "medicare": "downgraded"}
    assert verdict_line(v) == "Social Security upheld; Medicare downgraded"


def test_upheld_when_every_objection_is_rebutted():
    no_medicare = [{**p, "medicareCents": 0} for p in stubs_with_ids(paystubs())]
    _, _, _, v = hearing(PRIYA, no_medicare)
    assert v["verdict"] == "upheld"


def test_needs_human_when_employment_type_is_missing():
    _, _, rebuttals, v = hearing({**PRIYA, "employmentType": None}, stubs_with_ids(paystubs()))
    assert v["verdict"] == "needs_human" and "contractor" in v["reason"]


def test_needs_human_when_facts_conflict():
    _, _, _, v = hearing({**PRIYA, "employmentType": "contractor"}, stubs_with_ids(paystubs()))
    assert v["verdict"] == "needs_human"


def test_missing_arrival_date_stops_the_hearing():
    profile = {**PRIYA, "arrivalDate": None}
    claim = advocate.fica_claim(profile, stubs_with_ids(paystubs()), None, None, QUOTE_SOURCE)
    objs = objections(claim, profile)
    assert [o["id"] for o in objs] == ["missing_visa_or_arrival_data"]
    assert decide(claim, objs, [advocate.rebut(o, claim, profile) for o in objs])["verdict"] == "needs_human"


@pytest.mark.parametrize("name", ["09_sixth_year_plus.json", "10_sixth_year_plus.json",
                                  "11_sixth_year_plus.json", "12_sixth_year_plus.json"])
def test_auditor_wins_in_year_six(name):
    case = json.loads((Path("eval/profiles") / name).read_text())
    profile = {**case["profile"], "_id": "p6", "employmentType": "employee"}
    stubs = stubs_with_ids(case["paystubs"])
    assert fica_exempt(profile, stubs, case["schoolCalendar"], date.fromisoformat(case["asOf"])) is None
    claim = advocate.fica_claim(profile, stubs, None, None, QUOTE_SOURCE)
    assert claim is not None and not claim["rule_fired"] and min(claim["calendar_years"]) > 5
    objs = objections(claim, profile)
    v = decide(claim, objs, [advocate.rebut(o, claim, profile) for o in objs])
    assert v["verdict"] == "defeated" and "Auditor wins" in v["reason"]


def test_no_claim_without_withholding_or_f1():
    clean = [{**p, "ssCents": 0, "medicareCents": 0} for p in stubs_with_ids(paystubs())]
    assert advocate.fica_claim(PRIYA, clean, None, None, QUOTE_SOURCE) is None
    assert advocate.fica_claim({**PRIYA, "visa": "J-1"}, stubs_with_ids(paystubs()), None, None, QUOTE_SOURCE) is None


def test_arguments_quote_only_numbers_from_the_claim():
    claim, _, _, _ = hearing(PRIYA, stubs_with_ids(paystubs()))
    text = advocate.opening(claim, PRIYA)
    assert "$357.12" in text and "$83.52" in text and "$440.64" in text and "calendar year 3" in text
