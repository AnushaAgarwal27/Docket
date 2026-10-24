"""The answer key in eval/profiles was written by hand; the rules engine must agree with all 25."""
import json
from datetime import date
from pathlib import Path

import pytest

from rules.engine import evaluate, load_rules

PROFILES = sorted((Path(__file__).resolve().parents[1] / "eval" / "profiles").glob("*.json"))


def test_set_has_the_planned_mix():
    groups = [json.loads(p.read_text())["group"] for p in PROFILES]
    assert {g: groups.count(g) for g in set(groups)} == {
        "exempt_withheld": 8, "sixth_year_plus": 4, "clean": 4, "over_20": 5, "no_income_8843": 4}


@pytest.mark.parametrize("path", PROFILES, ids=lambda p: p.stem)
def test_engine_matches_answer_key(path):
    case = json.loads(path.read_text())
    rules = load_rules()
    sources = {r["source_id"]: r["quote"] for r in rules}
    out = evaluate(case["profile"], case["paystubs"], case["schoolCalendar"], date.fromisoformat(case["asOf"]),
                   sources, rules=rules)
    got = sorted((f["ruleId"], f["amountCents"]) for f in out.flags)
    assert got == sorted((e["ruleId"], e["amountCents"]) for e in case["expected"]), case["why"]
