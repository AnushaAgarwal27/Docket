"""Plain Claude vs Docket on the 25 eval profiles.

    .venv/bin/python -m eval.run                 # both arms (25 plain-Claude calls + 25 grader calls)
    .venv/bin/python -m eval.run --docket-only   # rules engine only, no API calls

Docket: the rules engine on the student's facts, with every quote checked against the stored
official source (Convex `sources`). Plain Claude: the facts plus one question, no tools, no
sources. A grader call reads each plain answer and records which issues it raised and any
clause it quoted; code then checks those quotes word for word against the same sources.

A profile is correct when the set of issues raised equals the answer key exactly.
Results go to eval/results/<timestamp>.json.
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

from agents.store import query
from rules.engine import evaluate, load_rules
from rules.quote_checker import check_quote

MODEL = "claude-opus-5"
PROFILES_DIR = Path(__file__).with_name("profiles")
RESULTS_DIR = Path(__file__).with_name("results")
QUESTION = "Is anything wrong with this student's pay or filings?"
FACT_KEYS = ("profile", "paystubs", "schoolCalendar", "asOf")  # never expected, why or group

GRADER_PROMPT = """You are grading an answer about an F-1 student's pay and filings.
Say which of these three issues the answer raises as a problem the student has:

- fica: Social Security and/or Medicare tax was withheld but the student is exempt and should get it back.
- over_20_hours: the student worked more than 20 hours in a week while school was in session.
- form_8843: the student needs to file Form 8843 (it is missing or due).

Count an issue only if the answer says it applies to this student. Mentioning a rule in passing,
or saying the student is fine on it, does not count. For fica, give the refund amount the answer
states in integer cents, or null if it gives none. Copy any sentence the answer presents as a
direct quotation from an official source exactly as written, without the quotation marks.

The answer:
<answer>
{answer}
</answer>"""

ISSUE_TO_RULE = {"fica": "FICA_EXEMPT_F1", "over_20_hours": "ONCAMPUS_20_HOURS", "form_8843": "FORM_8843_ANNUAL"}


class Grade(BaseModel):
    fica: bool
    over_20_hours: bool
    form_8843: bool
    fica_amount_cents: int | None
    quotes: list[str]


def load_profiles() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(PROFILES_DIR.glob("*.json"))]


def load_sources(rules: list[dict]) -> dict[str, str]:
    """source_id -> stored official text, from the shared file."""
    out = {}
    for rule in rules:
        row = query("sources:getByUrl", {"url": rule["source_url"]})
        if row is not None:
            out[rule["source_id"]] = row["text"]
    return out


def run_docket(case: dict, rules: list[dict], sources: dict[str, str]) -> dict:
    ev = evaluate(case["profile"], case["paystubs"], case["schoolCalendar"], date.fromisoformat(case["asOf"]),
                  sources, rules=rules)
    return {
        "raised": sorted(f["ruleId"] for f in ev.flags),
        "amounts": {f["ruleId"]: f["amountCents"] for f in ev.flags},
        "quotesChecked": len(ev.flags),
        "quotesVerified": len(ev.flags),  # the engine drops any flag whose quote fails
        "rejected": [a for a in ev.activity if a["action"] == "flag_rejected"],
    }


def ask_plain(client, case: dict) -> str:
    facts = json.dumps({k: case[k] for k in FACT_KEYS}, indent=2)
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": "high"},
        messages=[{"role": "user", "content": f"{facts}\n\n{QUESTION}"}],
    )
    if response.stop_reason == "refusal":
        return "(refused)"
    return "".join(b.text for b in response.content if b.type == "text")


def grade(client, answer: str) -> Grade:
    response = client.messages.parse(
        model=MODEL,
        max_tokens=4000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": GRADER_PROMPT.format(answer=answer)}],
        output_format=Grade,
    )
    if response.parsed_output is None:
        raise RuntimeError(f"grader returned nothing (stop_reason={response.stop_reason})")
    return response.parsed_output


def run_plain(client, case: dict, sources: dict[str, str]) -> dict:
    answer = ask_plain(client, case)
    g = grade(client, answer)
    raised = sorted(rule for issue, rule in ISSUE_TO_RULE.items() if getattr(g, issue))
    texts = list(sources.values())
    verified = sum(any(check_quote(q, t).ok for t in texts) for q in g.quotes)
    return {
        "raised": raised,
        "amounts": {"FICA_EXEMPT_F1": g.fica_amount_cents} if g.fica else {},
        "quotesChecked": len(g.quotes),
        "quotesVerified": verified,
        "answer": answer,
    }


def score(case: dict, arm: dict) -> dict:
    expected = {e["ruleId"]: e["amountCents"] for e in case["expected"]}
    raised = set(arm["raised"])
    fica_ok = None
    if "FICA_EXEMPT_F1" in expected and "FICA_EXEMPT_F1" in raised:
        fica_ok = arm["amounts"].get("FICA_EXEMPT_F1") == expected["FICA_EXEMPT_F1"]
    return {
        "correct": raised == set(expected),
        "falseFlags": sorted(raised - set(expected)),
        "missed": sorted(set(expected) - raised),
        "ficaAmountRight": fica_ok,
    }


def summarize(name: str, rows: list[dict]) -> str:
    n = len(rows)
    correct = sum(r["score"]["correct"] for r in rows)
    false_flags = sum(len(r["score"]["falseFlags"]) for r in rows)
    missed = sum(len(r["score"]["missed"]) for r in rows)
    quotes = sum(r["quotesChecked"] for r in rows)
    verified = sum(r["quotesVerified"] for r in rows)
    amounts = [r["score"]["ficaAmountRight"] for r in rows if r["score"]["ficaAmountRight"] is not None]
    return (f"{name:<13} {correct:>2}/{n} correct   {false_flags} false flags   {missed} missed   "
            f"quotes verified {verified}/{quotes}   FICA amount right {sum(amounts)}/{len(amounts)}")


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--docket-only", action="store_true")
    args = ap.parse_args()

    cases = load_profiles()
    rules = load_rules()
    sources = load_sources(rules)
    missing = [r["id"] for r in rules if r["source_id"] not in sources]
    if missing:
        raise SystemExit(f"sources not fetched for {missing}; run python -m seed.fetch_sources")

    docket = []
    for case in cases:
        arm = run_docket(case, rules, sources)
        docket.append({"id": case["id"], "group": case["group"], **arm, "score": score(case, arm)})

    plain = []
    if not args.docket_only:
        import anthropic
        client = anthropic.Anthropic()
        with ThreadPoolExecutor(max_workers=5) as pool:
            arms = list(pool.map(lambda c: run_plain(client, c, sources), cases))
        plain = [{"id": c["id"], "group": c["group"], **a, "score": score(c, a)} for c, a in zip(cases, arms)]

    print(f"{'profile':<22} {'expected':<34} {'docket':<34} plain claude")
    for i, case in enumerate(cases):
        exp = ",".join(e["ruleId"] for e in case["expected"]) or "-"
        d = docket[i]
        cells = [f"{'ok ' if d['score']['correct'] else 'XX '}{','.join(d['raised']) or '-'}"]
        if plain:
            p = plain[i]
            cells.append(f"{'ok ' if p['score']['correct'] else 'XX '}{','.join(p['raised']) or '-'}")
        print(f"{case['id'] + ' ' + case['group']:<22} {exp:<34} " + " ".join(f"{c:<34}" for c in cells))
    print()
    print(summarize("Docket", docket))
    if plain:
        print(summarize("Plain Claude", plain))

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    out.write_text(json.dumps({"model": MODEL, "question": QUESTION, "docket": docket, "plain": plain}, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
