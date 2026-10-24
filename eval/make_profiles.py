"""Writes the 25 synthetic eval profiles to eval/profiles/*.json.

Each file has the student's facts and the answer key. Answers are written here by hand from the
rules (not by running the engine); tests/test_eval_profiles.py checks the engine agrees.

    python -m eval.make_profiles
"""
import json
from datetime import date, timedelta
from pathlib import Path

from seed.demo_data import SCHOOL_CALENDAR, make_paystub

OUT = Path(__file__).with_name("profiles")
AS_OF = "2026-10-24"
NAMES = ["Aarav Mehta", "Mei Lin", "Oluwaseun Adeyemi", "Sofia Rossi", "Hiroshi Tanaka", "Fatima Khan",
         "Lucas Silva", "Ananya Iyer", "Chen Wei", "Yusuf Demir", "Nadia Petrova", "Kwame Mensah",
         "Isabela Costa", "Jae-won Park", "Amira Haddad", "Diego Herrera", "Leila Rahimi", "Tomas Novak",
         "Zara Ahmed", "Minh Nguyen", "Elif Yildiz", "Rahul Verma", "Chiara Bianchi", "Daniel Osei", "Sara Haile"]


def exempt_years_before(arrival, year):
    """Every exempt calendar year (the first 5, counting the arrival year) before `year`."""
    first = int(arrival[:4])
    return [y for y in range(first, min(first + 5, year))]


def profile(name, arrival, filed=None, visa="F-1"):
    """`filed` defaults to every past exempt year, so only the 8843 cases are missing one."""
    if filed is None:
        filed = exempt_years_before(arrival, 2026)
    return {"name": name, "visa": visa, "arrivalDate": arrival, "school": "Golden Bear University",
            "homeCountry": "Synthetic", "homeCurrency": "USD", "workAuth": "on-campus",
            "phoneMasked": "(***) ***-0000", "filed8843Years": list(filed)}


def stubs(first_start, n, hours=(20, 20), rate=1800, withhold=True, split=None):
    """n biweekly paystubs. `split` = (index, hours_by_week) overrides one stub's weekly hours."""
    out = []
    for i in range(n):
        start = date.fromisoformat(first_start) + timedelta(days=14 * i)
        h = list(split[1]) if split and split[0] == i else list(hours)
        s = make_paystub(i + 1, start, h)
        if rate != 1800:  # make_paystub uses the demo rate; rescale gross and withholding
            gross = sum(h) * rate
            s.update(grossCents=gross, ssCents=(gross * 620 + 5000) // 10000,
                     medicareCents=(gross * 145 + 5000) // 10000)
        if not withhold:
            s.update(ssCents=0, medicareCents=0)
        s["netCents"] = s["grossCents"] - s["ssCents"] - s["medicareCents"]
        out.append(s)
    return out


def fica(paystubs):
    return {"ruleId": "FICA_EXEMPT_F1", "amountCents": sum(s["ssCents"] + s["medicareCents"] for s in paystubs)}


CASES = []


def case(group, why, prof, paystubs, expected, as_of=AS_OF):
    CASES.append({"group": group, "why": why, "asOf": as_of, "profile": prof,
                  "schoolCalendar": SCHOOL_CALENDAR, "paystubs": paystubs, "expected": expected})


# 8 exempt students with Social Security and Medicare wrongly withheld: flag.
for i, (arrival, n, rate) in enumerate([("2024-08-15", 8, 1800), ("2025-08-20", 6, 1650), ("2026-01-05", 4, 1700),
                                        ("2023-08-22", 8, 1900), ("2022-08-18", 5, 2000), ("2022-01-10", 3, 1800),
                                        ("2025-01-08", 7, 1750), ("2023-12-28", 2, 2100)]):
    p = stubs("2026-01-12", n, rate=rate)
    year = 2026 - int(arrival[:4]) + 1
    case("exempt_withheld", f"F-1, 2026 is calendar year {year} of 5, FICA withheld", profile(NAMES[i], arrival), p, [fica(p)])

# 4 students in their 6th calendar year or later: withholding is correct, no flag.
for i, arrival in enumerate(["2021-08-16", "2020-08-17", "2019-01-07", "2021-12-30"]):
    year = 2026 - int(arrival[:4]) + 1
    case("sixth_year_plus", f"2026 is calendar year {year}; no longer exempt, so withholding is correct",
         profile(NAMES[8 + i], arrival), stubs("2026-01-12", 6), [])

# 4 clean paystubs, nothing withheld: no flag.
for i, arrival in enumerate(["2024-08-15", "2025-08-20", "2023-08-21", "2026-01-06"]):
    case("clean", "exempt and nothing withheld", profile(NAMES[12 + i], arrival), stubs("2026-01-12", 6, withhold=False), [])

# 5 with a week over 20 hours; the winter-break one is allowed.
over = [("2026-01-12", (2, (12, 26)), "2026-02-16", 26), ("2026-01-12", (0, (22, 18)), "2026-01-12", 22),
        ("2026-08-31", (2, (21, 19)), "2026-09-28", 21), ("2025-09-01", (5, (18, 30)), "2025-11-17", 30)]
for i, (start, split, week, hours) in enumerate(over):
    case("over_20", f"{hours} hours in the week of {week}, school in session",
         profile(NAMES[16 + i], "2024-08-15"), stubs(start, split[0] + 1, withhold=False, split=split),
         [{"ruleId": "ONCAMPUS_20_HOURS", "amountCents": 0}])
case("over_20", "30 hours in the weeks of 2025-12-22 and 2025-12-29: winter break, the limit does not apply",
     profile(NAMES[20], "2024-08-15"), stubs("2025-12-22", 1, hours=(30, 30), withhold=False), [])

# 4 with no income at all: still need Form 8843.
for i, (arrival, as_of, deadline) in enumerate([("2025-08-20", "2026-02-01", "2026-06-15"), ("2024-08-15", "2026-03-15", "2026-06-15"),
                                                ("2023-08-21", AS_OF, "2026-06-15"), ("2025-01-10", "2026-05-01", "2026-06-15")]):
    case("no_income_8843", f"F-1 with no US income, no 8843 on record for 2025 (due {deadline})",
         profile(NAMES[21 + i], arrival, filed=exempt_years_before(arrival, 2025)), [], [{"ruleId": "FORM_8843_ANNUAL", "amountCents": 0}], as_of=as_of)


def main():
    OUT.mkdir(exist_ok=True)
    assert len(CASES) == 25, len(CASES)
    for i, c in enumerate(CASES, 1):
        (OUT / f"{i:02d}_{c['group']}.json").write_text(json.dumps({"id": f"{i:02d}", **c}, indent=2) + "\n")
    print(f"Wrote {len(CASES)} profiles to {OUT}")


if __name__ == "__main__":
    main()
