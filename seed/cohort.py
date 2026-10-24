"""A simulated cohort for the employer pattern view: six made-up students beside Priya.

    python -m seed.cohort        # also runs at the end of `python -m seed.reset` (skip with --no-cohort)

Every profile is marked simulated and named "Simulated student N". Their flags come from the real rules
engine and quote checker against the stored official sources, the same path Priya's flags take, so the
pattern counts are computed, not typed in. Expected result: University Dining Services has 4 students
flagged (Priya plus three) and is highlighted; Campus Library has 1 of 2.
"""
from __future__ import annotations

from datetime import date, timedelta

from agents.store import log, mutation, query
from agents.tax.engine import explain
from rules.engine import evaluate, load_rules
from seed.demo_data import SCHOOL_CALENDAR, pct_of

RATE_CENTS = 1700
# (employer, arrival date, withheld?) -- one per simulated student
COHORT = [
    ("University Dining Services", "2025-08-20", True),   # calendar year 2: exempt, withheld -> flagged
    ("University Dining Services", "2023-09-01", True),   # year 4 -> flagged
    ("University Dining Services", "2024-01-10", True),   # year 3 -> flagged
    ("University Dining Services", "2020-08-15", True),   # year 7: withholding is correct -> not flagged
    ("Campus Library", "2025-01-05", True),               # year 2 -> flagged
    ("Campus Library", "2024-08-20", False),              # nothing withheld -> clean
]


def stubs_for(profile_id: str, employer: str, withheld: bool, n: int) -> list[dict]:
    out = []
    start = date(2026, 1, 12)
    for i in range(4):
        s = start + timedelta(days=14 * i)
        gross = 30 * RATE_CENTS
        ss = pct_of(gross, 620) if withheld else 0
        med = pct_of(gross, 145) if withheld else 0
        out.append({
            "profileId": profile_id, "periodStart": s.isoformat(), "periodEnd": (s + timedelta(days=13)).isoformat(),
            "employer": employer, "grossCents": gross, "hoursByWeek": [15, 15], "ssCents": ss, "medicareCents": med,
            "netCents": gross - ss - med, "sourceFile": f"simulated_{n:02d}_{i + 1:02d}",
        })
    return out


def seed_cohort(as_of: date | None = None) -> dict:
    as_of = as_of or date.today()
    rules = load_rules()
    sources, source_ids = {}, {}
    for r in rules:
        s = query("sources:getByUrl", {"url": r["source_url"]})
        if s is not None:
            sources[r["source_id"]], source_ids[r["source_id"]] = s["text"], s["_id"]
    flagged = 0
    for n, (employer, arrival, withheld) in enumerate(COHORT, start=1):
        arrival_year = int(arrival[:4])
        profile = {
            "name": f"Simulated student {n}", "visa": "F-1", "arrivalDate": arrival, "school": SCHOOL_CALENDAR["school"],
            "homeCountry": "Simulated", "homeCurrency": "USD", "workAuth": "on-campus", "phoneMasked": "",
            "filed8843Years": list(range(arrival_year, as_of.year)),  # nothing else to flag but the pattern under test
        }
        pid = mutation("seed:addSimulatedStudent", {"profile": profile})
        stubs = stubs_for(pid, employer, withheld, n)
        for stub in stubs:
            mutation("paystubs:record", stub)
        result = evaluate({**profile, "_id": pid}, stubs, SCHOOL_CALENDAR, as_of, sources, rules)
        for f in result.flags:
            mutation("flags:upsert", {
                "profileId": pid, "ruleId": f["ruleId"], "amountCents": f["amountCents"],
                "explanation": explain(f["ruleId"], f["detail"]), "quote": f["quote"],
                "sourceId": source_ids[f["sourceId"]], "status": "open",
            })
            flagged += f["ruleId"] == "FICA_EXEMPT_F1"
    missing = [r["id"] for r in rules if r["source_id"] not in sources]
    log("seed", "simulated_cohort",
        f"Seeded {len(COHORT)} simulated students for the employer pattern view; {flagged} flagged by the rules engine"
        + (f" (no stored source for {', '.join(missing)})" if missing else ""))
    return {"students": len(COHORT), "flagged": flagged, "missingSources": missing}


if __name__ == "__main__":
    print(seed_cohort())
