"""Docket's rules engine on the eval profiles, scored as caught / total with false flags.

    python -m eval.score               # quotes checked against sources/*.txt (rules.download_sources)
    python -m eval.score --stand-in    # no downloads: each source is just its rule's quote

A catch is an expected (profile, rule) pair raised with the right amount. A false flag is a
raised pair the answer key doesn't have.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from rules.engine import evaluate, load_local_sources, load_rules

PROFILES_DIR = Path(__file__).with_name("profiles")


def load_cases() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(PROFILES_DIR.glob("*.json"))]


def run_case(case: dict, rules: list[dict], sources: dict[str, str]):
    return evaluate(case["profile"], case["paystubs"], case["schoolCalendar"], date.fromisoformat(case["asOf"]),
                    sources, rules=rules)


def score(cases: list[dict], raised: list[dict[str, int]]) -> dict:
    """`raised[i]` maps ruleId -> amountCents for case i. Works for any arm, not just Docket."""
    caught, total, false_flags, missed = 0, 0, [], []
    for case, got in zip(cases, raised):
        want = {e["ruleId"]: e["amountCents"] for e in case["expected"]}
        total += len(want)
        for rule, cents in want.items():
            if got.get(rule) == cents:
                caught += 1
            else:
                missed.append(f"{case['id']} {rule}")
        false_flags += [f"{case['id']} {rule}" for rule in got if rule not in want]
    return {"caught": caught, "total": total, "falseFlags": false_flags, "missed": missed,
            "profiles": len(cases)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stand-in", action="store_true")
    args = ap.parse_args()
    rules = load_rules()
    sources = {r["source_id"]: r["quote"] for r in rules} if args.stand_in else load_local_sources(rules)
    cases = load_cases()
    raised = [{f["ruleId"]: f["amountCents"] for f in run_case(c, rules, sources).flags} for c in cases]
    s = score(cases, raised)
    print(f"Docket: caught {s['caught']}/{s['total']}, {len(s['falseFlags'])} false flags, "
          f"{len(s['missed'])} missed, across {s['profiles']} profiles")
    for label in ("falseFlags", "missed"):
        for item in s[label]:
            print(f"  {label}: {item}")


if __name__ == "__main__":
    main()
