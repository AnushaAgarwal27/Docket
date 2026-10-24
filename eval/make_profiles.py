"""Writes the 31 synthetic eval profiles to eval/profiles/*.json.

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
         "Zara Ahmed", "Minh Nguyen", "Elif Yildiz", "Rahul Verma", "Chiara Bianchi", "Daniel Osei", "Sara Haile",
         "Arjun Nair", "Ingrid Larsen", "Kofi Boateng", "Valentina Cruz", "Hana Sato", "Omar Farouk"]

DINING = {"name": "Golden Bear Dining Services", "type": "university"}  # shared by three students
CONTRACTOR = {"name": "Bear Hospitality LLC", "type": "contractor"}
CAMPUS_JOBS = [{"name": n, "type": "university"} for n in (
    "Golden Bear University Library", "Recreational Sports", "Residential Life", "Engineering Computer Lab")]
EXEMPT_YEARS = {"F-1": 5, "J-1 student": 5, "J-1 scholar": 2}


def exempt_years_before(arrival, year, limit=5):
    """Every exempt calendar year (the first `limit`, counting the arrival year) before `year`."""
    first = int(arrival[:4])
    return [y for y in range(first, min(first + limit, year))]


def profile(name, arrival, filed=None, visa="F-1", employer=None, j1=None, software=None):
    """`filed` defaults to every past exempt year, so only the 8843 cases are missing one."""
    status = f"J-1 {j1}" if visa == "J-1" else visa
    if filed is None:
        filed = exempt_years_before(arrival, 2026, EXEMPT_YEARS.get(status, 5))
    p = {"name": name, "visa": visa, "arrivalDate": arrival, "school": "Golden Bear University",
         "homeCountry": "Synthetic", "homeCurrency": "USD", "workAuth": "on-campus",
         "phoneMasked": "(***) ***-0000", "filed8843Years": list(filed),
         "employer": employer or CAMPUS_JOBS[len(CASES) % len(CAMPUS_JOBS)]}
    if j1:
        p["j1Category"] = j1
    if software:
        p["taxSoftware"] = software
    return p


def stubs(first_start, n, hours=(20, 20), rate=1800, withhold=True, split=None, ss_override=None):
    """n biweekly paystubs. `split` = (index, hours_by_week) overrides one stub's weekly hours.
    `ss_override` sets a Social Security amount that is not 6.2% of gross (a misread or odd payroll)."""
    out = []
    for i in range(n):
        start = date.fromisoformat(first_start) + timedelta(days=14 * i)
        h = list(split[1]) if split and split[0] == i else list(hours)
        s = make_paystub(i + 1, start, h)
        if rate != 1800:  # make_paystub uses the demo rate; rescale gross and withholding
            gross = sum(h) * rate
            s.update(grossCents=gross, ssCents=(gross * 620 + 5000) // 10000,
                     medicareCents=(gross * 145 + 5000) // 10000)
        if ss_override is not None:
            s["ssCents"] = ss_override
        if not withhold:
            s.update(ssCents=0, medicareCents=0)
        s["netCents"] = s["grossCents"] - s["ssCents"] - s["medicareCents"]
        out.append(s)
    return out


def fica(paystubs):
    return {"ruleId": "FICA_EXEMPT_F1", "amountCents": sum(s["ssCents"] + s["medicareCents"] for s in paystubs)}


CASES = []


def case(group, why, prof, paystubs, expected, as_of=AS_OF, detail=None, reasons=None):
    """`detail` pins fields of a raised flag's detail; `reasons` pins why a rule did not flag."""
    for s in paystubs:
        s["employer"] = prof["employer"]["name"]
    c = {"group": group, "why": why, "asOf": as_of, "profile": prof,
         "schoolCalendar": SCHOOL_CALENDAR, "paystubs": paystubs, "expected": expected}
    if detail:
        c["expectedDetail"] = detail
    if reasons:
        c["expectedReasons"] = reasons
    CASES.append(c)


# 8 exempt students with Social Security and Medicare wrongly withheld: flag. Three share one employer.
for i, (arrival, n, rate) in enumerate([("2024-08-15", 8, 1800), ("2025-08-20", 6, 1650), ("2026-01-05", 4, 1700),
                                        ("2023-08-22", 8, 1900), ("2022-08-18", 5, 2000), ("2022-01-10", 3, 1800),
                                        ("2025-01-08", 7, 1750), ("2023-12-28", 2, 2100)]):
    p = stubs("2026-01-12", n, rate=rate)
    year = 2026 - int(arrival[:4]) + 1
    employer = DINING if i in (0, 1, 3) else None
    case("exempt_withheld", f"F-1, 2026 is calendar year {year} of 5, FICA withheld",
         profile(NAMES[i], arrival, employer=employer), p, [fica(p)],
         detail={"FICA_EXEMPT_F1": {"basis": "f1_nra_exempt", "confidence": {"social_security": "high", "medicare": "high"}}})

# 4 students in their 6th calendar year or later: withholding is correct, no flag. 2021 arrivals are exactly year 6.
for i, arrival in enumerate(["2021-08-16", "2020-08-17", "2019-01-07", "2021-12-30"]):
    year = 2026 - int(arrival[:4]) + 1
    case("sixth_year_plus", f"2026 is calendar year {year}; no longer exempt, so withholding is correct",
         profile(NAMES[8 + i], arrival), stubs("2026-01-12", 6), [],
         reasons={"FICA_EXEMPT_F1": f"calendar year {year} on F-1 is past the 5-year exemption"})

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
         profile(NAMES[21 + i], arrival, filed=exempt_years_before(arrival, 2025)), [],
         [{"ruleId": "FORM_8843_ANNUAL", "amountCents": 0}], as_of=as_of)

# 2 J-1 scholars: exempt for 2 calendar years, not 5.
p = stubs("2026-01-12", 6, rate=2500)
case("j1_scholar", "J-1 scholar, 2026 is calendar year 2 of 2, FICA withheld",
     profile(NAMES[25], "2025-07-01", visa="J-1", j1="scholar"), p, [fica(p)],
     detail={"FICA_EXEMPT_F1": {"basis": "f1_nra_exempt", "exemptYears": 2}})
case("j1_scholar", "J-1 scholar, 2026 is calendar year 3: past the 2-year exemption, withholding is correct",
     profile(NAMES[26], "2024-07-01", visa="J-1", j1="scholar"), stubs("2026-01-12", 6, rate=2500), [],
     reasons={"FICA_EXEMPT_F1": "calendar year 3 on J-1 scholar is past the 2-year exemption"})

# Employer is a contractor: still exempt as a nonresident, but the student exception can't apply.
p = stubs("2026-01-12", 5)
case("contractor", "F-1 year 2 working for a dining contractor, FICA withheld; basis is nonresident status only",
     profile(NAMES[27], "2025-08-20", employer=CONTRACTOR), p, [fica(p)],
     detail={"FICA_EXEMPT_F1": {"basis": "f1_nra_exempt", "studentException": {"applies": False}}})

# Social Security line is not 6.2% of gross: still flag what was withheld, at lower confidence.
p = stubs("2026-01-12", 4, ss_override=5000)
case("mismatch", "F-1 year 3, Social Security withheld is $50.00, not 6.2% of $720.00 gross; Medicare matches",
     profile(NAMES[28], "2024-08-15"), p, [fica(p)],
     detail={"FICA_EXEMPT_F1": {"confidence": {"social_security": "medium", "medicare": "high"}}})

# Filed last year's return with resident-only software: warn.
case("wrong_form", "F-1 nonresident in 2025 who filed with TurboTax, which only prepares Form 1040",
     profile(NAMES[29], "2024-08-15", software="TurboTax"), stubs("2026-01-12", 4, withhold=False),
     [{"ruleId": "WRONG_TAX_FORM", "amountCents": 0}])

# Visa unknown: no flag of any kind, with a reason.
case("unknown_visa", "visa not recorded, FICA withheld: can't count exempt years, so no flag",
     profile(NAMES[30], "2024-08-15", visa=""), stubs("2026-01-12", 4), [],
     reasons={"FICA_EXEMPT_F1": "visa unknown", "FORM_8843_ANNUAL": "visa unknown"})


def main():
    OUT.mkdir(exist_ok=True)
    assert len(CASES) == 31, len(CASES)
    for old in OUT.glob("*.json"):
        old.unlink()
    for i, c in enumerate(CASES, 1):
        (OUT / f"{i:02d}_{c['group']}.json").write_text(json.dumps({"id": f"{i:02d}", **c}, indent=2) + "\n")
    print(f"Wrote {len(CASES)} profiles to {OUT}")


if __name__ == "__main__":
    main()
