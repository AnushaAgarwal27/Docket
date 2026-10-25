import json
from datetime import date

from agents.coordinator.cards import finding_detail, profile_form, refund_review, validate
from agents.coordinator.profile_form import form_changes

REQUIRED = {"card_protocol_version": "1", "requires_card_interaction": "true"}


def check(card, kind):
    meta = card.metadata()
    assert validate(card) == []
    assert all(isinstance(v, str) for v in meta.values())
    assert {k: meta[k] for k in REQUIRED} == REQUIRED and meta["card_kind"] == kind
    payload = json.loads(meta["card_payload"])
    assert "title" in payload and len(meta["card_payload"].encode()) <= 64 * 1024
    return payload


def test_form_card_matches_the_schema():
    p = check(profile_form(), "form")
    selects = [f for f in p["fields"] if f["kind"] == "select"]
    assert selects and all(f["options"] and {"value", "label"} <= set(f["options"][0]) for f in selects)
    assert p["submit_cta"]["selection"] == {"action": "submit_profile"}


def test_detail_card_matches_the_schema():
    card = finding_detail("Social Security and Medicare withheld", [("Social Security", "$357.12 · high confidence"),
                          ("Medicare", "$83.52 · medium confidence")], "quote text", "IRS Publication 519",
                          "Social Security upheld; Medicare downgraded", "flag_1", "Here is the finding.")
    p = check(card, "detail")
    assert p["ctas"][0]["selection"] == {"action": "show_hearing", "flag_id": "flag_1"}


def test_review_card_approve_and_reject_are_different_actions():
    p = check(refund_review("University Dining Services", 44064, 35712, 8352, "upheld", "case_1", None, "Approve?"),
              "review")
    assert p["approve_cta"]["selection"] == {"action": "approve_refund", "case_id": "case_1"}
    assert p["reject_cta"]["selection"]["action"] == "decline_refund"
    assert {"label": "Refund requested", "value": "$440.64"} in p["summary_rows"]


def test_invalid_card_is_caught():
    card = refund_review("X", 1, None, None, "upheld", None, None, "t")
    card.payload["approve_cta"] = {"label": "Approve"}  # no selection
    assert validate(card) == ["approve_cta needs a label and a selection object"]


def test_form_values_are_checked_before_saving():
    changes, problems = form_changes({"action": "submit_profile", "arrival_date": "2024-08-15", "visa_type": "f-1",
                                      "employer": "University Dining Services", "employment_type": "employee",
                                      "employer_is_school": True, "enrolled": "yes"}, date(2026, 10, 24))
    assert problems == [] and changes == {"arrivalDate": "2024-08-15", "visa": "F-1", "employer": "University Dining Services",
                                          "employmentType": "employee", "employerIsSchool": True, "enrolled": True}
    _, problems = form_changes({"arrival_date": "next year", "employment_type": "intern"}, date(2026, 10, 24))
    assert len(problems) == 2
    _, problems = form_changes({"arrival_date": "2030-01-01"}, date(2026, 10, 24))
    assert problems == ["arrival date must be a real date, not in the future"]
