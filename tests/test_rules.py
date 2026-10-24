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


from rules.rules import NoFlag, decide_fica_exempt, decide_needs_8843, decide_resident_tax_software


def test_ss_and_medicare_are_separate_findings_with_their_own_confidence():
    hit = fica_exempt(d.PROFILE, d.paystubs(), CAL, AS_OF)
    parts = {f["part"]: f for f in hit["findings"]}
    assert parts["social_security"]["amountCents"] == 35712 and parts["medicare"]["amountCents"] == 8352
    assert parts["social_security"]["confidence"] == parts["medicare"]["confidence"] == "high"


def test_off_rate_line_lowers_only_its_own_confidence():
    stubs = [{**s, "ssCents": 5000} for s in d.paystubs()]
    parts = {f["part"]: f for f in fica_exempt(d.PROFILE, stubs, CAL, AS_OF)["findings"]}
    assert parts["social_security"]["confidence"] == "medium" and parts["medicare"]["confidence"] == "high"
    assert "not 6.20% of gross ($44.64)" in parts["social_security"]["confidenceReasons"][0]


def test_amounts_are_precomputed_per_paycheck_per_line_and_total():
    a = fica_exempt(d.PROFILE, d.paystubs(), CAL, AS_OF)["amounts"]
    assert a["display"] == {"total": "$440.64", "socialSecurity": "$357.12", "medicare": "$83.52", "perPaycheck": "$55.08"}
    assert a["perPaycheckCents"] == 5508 and a["paychecks"] == 8 and a["perPaycheck"][0]["display"] == "$55.08"


def test_only_medicare_withheld_gives_one_finding():
    stubs = [{**s, "ssCents": 0} for s in d.paystubs()]
    assert [f["part"] for f in fica_exempt(d.PROFILE, stubs, CAL, AS_OF)["findings"]] == ["medicare"]


def test_year_5_flags_year_6_does_not():
    assert fica_exempt({**d.PROFILE, "arrivalDate": "2022-08-15"}, d.paystubs(), CAL, AS_OF) is not None
    result = decide_fica_exempt({**d.PROFILE, "arrivalDate": "2021-08-15"}, d.paystubs(), CAL, AS_OF)
    assert isinstance(result, NoFlag) and "calendar year 6" in result.reason


def test_j1_scholar_is_exempt_for_two_years():
    scholar = {**d.PROFILE, "visa": "J-1", "j1Category": "scholar"}
    assert fica_exempt({**scholar, "arrivalDate": "2025-07-01"}, d.paystubs(), CAL, AS_OF)["exemptYears"] == 2
    assert fica_exempt({**scholar, "arrivalDate": "2024-07-01"}, d.paystubs(), CAL, AS_OF) is None


def test_j1_student_is_exempt_for_five_years():
    student = {**d.PROFILE, "visa": "J-1", "j1Category": "student", "arrivalDate": "2022-08-15"}
    assert fica_exempt(student, d.paystubs(), CAL, AS_OF) is not None


def test_unknown_visa_year_count_or_j1_category_means_no_flag_with_reason():
    for profile, reason in (({**d.PROFILE, "visa": ""}, "visa unknown"),
                            ({**d.PROFILE, "visa": "J-1"}, "J-1 category unknown"),
                            ({**d.PROFILE, "arrivalDate": None}, "arrival date unknown"),
                            ({**d.PROFILE, "visa": "H-1B"}, "not an F-1 or J-1")):
        result = decide_fica_exempt(profile, d.paystubs(), CAL, AS_OF)
        assert isinstance(result, NoFlag) and reason in result.reason


def test_basis_is_nonresident_status_and_contractor_rules_out_student_exception():
    hit = fica_exempt({**d.PROFILE, "employer": {"name": "Bear Hospitality LLC", "type": "contractor"}},
                      d.paystubs(), CAL, AS_OF)
    assert hit["basis"] == "f1_nra_exempt" and hit["studentException"]["applies"] is False
    school = fica_exempt({**d.PROFILE, "employer": {"name": "Dining", "type": "university"}}, d.paystubs(), CAL, AS_OF)
    assert school["basis"] == "f1_nra_exempt" and school["studentException"]["applies"] is None


def test_j1_scholar_8843_uses_two_year_count():
    scholar = {**d.PROFILE, "visa": "J-1", "j1Category": "scholar", "arrivalDate": "2023-07-01", "filed8843Years": []}
    assert isinstance(decide_needs_8843(scholar, [], CAL, date(2026, 2, 1)), NoFlag)  # 2025 is year 3


def test_resident_tax_software_warns_nonresident():
    hit = decide_resident_tax_software({**d.PROFILE, "taxSoftware": "TurboTax"}, [], CAL, AS_OF)
    assert hit.detail == {"amountCents": 0, "severity": "warning", "software": "TurboTax", "taxYear": 2025,
                          "expectedForm": "1040-NR"}


def test_nonresident_software_or_resident_student_does_not_warn():
    assert isinstance(decide_resident_tax_software({**d.PROFILE, "taxSoftware": "Sprintax"}, [], CAL, AS_OF), NoFlag)
    resident = {**d.PROFILE, "taxSoftware": "TurboTax", "arrivalDate": "2019-08-15"}
    assert isinstance(decide_resident_tax_software(resident, [], CAL, AS_OF), NoFlag)
    assert isinstance(decide_resident_tax_software(d.PROFILE, [], CAL, AS_OF), NoFlag)
