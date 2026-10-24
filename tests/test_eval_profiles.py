"""The answer key in eval/profiles was written by hand; the rules engine must agree with all 31."""
import json
from datetime import date
from pathlib import Path

import pytest

from rules.engine import evaluate, load_rules

PROFILES = sorted((Path(__file__).resolve().parents[1] / "eval" / "profiles").glob("*.json"))


def test_set_has_the_planned_mix():
    groups = [json.loads(p.read_text())["group"] for p in PROFILES]
    assert {g: groups.count(g) for g in set(groups)} == {
        "exempt_withheld": 8, "sixth_year_plus": 4, "clean": 4, "over_20": 5, "no_income_8843": 4,
        "j1_scholar": 2, "contractor": 1, "mismatch": 1, "wrong_form": 1, "unknown_visa": 1}


def test_three_students_share_one_employer():
    employers = [json.loads(p.read_text())["profile"]["employer"]["name"] for p in PROFILES]
    assert employers.count("Golden Bear Dining Services") == 3


@pytest.mark.parametrize("path", PROFILES, ids=lambda p: p.stem)
def test_engine_matches_answer_key(path):
    case = json.loads(path.read_text())
    rules = load_rules()
    sources = {r["source_id"]: r["quote"] for r in rules}
    out = evaluate(case["profile"], case["paystubs"], case["schoolCalendar"], date.fromisoformat(case["asOf"]),
                   sources, rules=rules)
    got = sorted((f["ruleId"], f["amountCents"]) for f in out.flags)
    assert got == sorted((e["ruleId"], e["amountCents"]) for e in case["expected"]), case["why"]
    flags = {f["ruleId"]: f["detail"] for f in out.flags}
    for rule_id, want in case.get("expectedDetail", {}).items():
        detail = flags[rule_id]
        for key, value in want.items():
            if key == "confidence":
                assert {f["part"]: f["confidence"] for f in detail["findings"]} == value, case["why"]
            elif isinstance(value, dict):
                assert {k: detail[key][k] for k in value} == value, case["why"]
            else:
                assert detail[key] == value, case["why"]
    reasons = {a["ruleId"]: a["detail"] for a in out.activity if a["action"] == "rule_not_triggered"}
    for rule_id, reason in case.get("expectedReasons", {}).items():
        assert reason in reasons[rule_id], case["why"]
