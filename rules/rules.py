"""Rule checks. Each is a pure function of facts; code does all math, counting and decisions.

A decision is a `Hit` (the rule applies; `detail` has `amountCents` plus everything the
explanation and the dashboard need) or a `NoFlag` with the reason it does not apply. Dates are
ISO strings, money is integer cents, and every dollar string a model might repeat is
precomputed here so Claude never does arithmetic.

`CHECKS` keeps the older contract (detail dict or None) for callers that only need yes or no.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

SS_RATE_BP = 620  # 6.20% in basis points
MEDICARE_RATE_BP = 145  # 1.45%
WEEKLY_HOUR_LIMIT = 20

# Calendar years a visa holder counts as an exempt individual (nonresident for FICA and the
# substantial presence test). Counted from the arrival year only: earlier US visits are not
# recorded, so a returning J-1 scholar may be over-counted as exempt.
EXEMPT_YEARS = {("F-1", None): 5, ("J-1", "student"): 5, ("J-1", "scholar"): 2}
EXEMPT_CALENDAR_YEARS = EXEMPT_YEARS[("F-1", None)]  # the F-1 student count, for callers that predate J-1
F1_NRA_EXEMPT = "f1_nra_exempt"  # nonresident alien on F/J status: IRC 3121(b)(19)
STUDENT_EXCEPTION = "student_exception"  # enrolled student working for their own school: IRC 3121(b)(10)

OPT_UNEMPLOYMENT_LIMIT = 90  # post-completion OPT, 8 CFR 214.2(f)(10)(ii)(E)
OPT_WARN_AT = 60  # warn with 30 days left

# Consumer software that only prepares the resident return (Form 1040).
RESIDENT_TAX_SOFTWARE = {"turbotax", "h&r block", "taxact", "freetaxusa", "cash app taxes", "taxslayer",
                         "credit karma tax", "jackson hewitt"}


@dataclass(frozen=True)
class Hit:
    detail: dict


@dataclass(frozen=True)
class NoFlag:
    reason: str


def money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    return f"{sign}${abs(cents) // 100:,}.{abs(cents) % 100:02d}"


def pct_of(cents: int, basis_points: int) -> int:
    """Integer percentage, rounded half up. 72000 * 620 bp = 4464."""
    return (cents * basis_points + 5000) // 10000


def calendar_year_number(arrival_date: str, year: int) -> int:
    """Which calendar year of US presence `year` is. Any part of a year counts as a full year,
    so arriving August 2024 makes 2024 year 1, 2025 year 2 and 2026 year 3."""
    return year - date.fromisoformat(arrival_date).year + 1


def exempt_years(profile: dict) -> int | NoFlag:
    """How many calendar years this student is exempt, or why that can't be known."""
    visa = profile.get("visa")
    if visa == "J-1":
        category = profile.get("j1Category")
        if category not in ("student", "scholar"):
            return NoFlag("J-1 category unknown (student or scholar), so the exempt years can't be counted")
        key = ("J-1", category)
    elif visa == "F-1":
        key = ("F-1", None)
    elif not visa:
        return NoFlag("visa unknown")
    else:
        return NoFlag(f"{visa} is not an F-1 or J-1 status")
    try:
        date.fromisoformat(profile.get("arrivalDate") or "")
    except ValueError:
        return NoFlag("arrival date unknown, so the calendar year count is unknown")
    return EXEMPT_YEARS[key]


def status_label(profile: dict) -> str:
    return f"J-1 {profile['j1Category']}" if profile.get("visa") == "J-1" else profile["visa"]


def student_exception(profile: dict) -> dict:
    """Whether the student FICA exception also supports a refund. Informational: flags rest on
    f1_nra_exempt. It needs the school itself as employer, so a contractor rules it out."""
    kind = (profile.get("employer") or {}).get("type")
    if kind == "contractor":
        return {"applies": False, "reason": "employer is a contractor, not the school, so the student exception does not apply"}
    if kind == "university":
        return {"applies": None, "reason": "employer is the school; the exception may also apply if she is enrolled at least half time"}
    return {"applies": None, "reason": "employer type unknown"}


def _week_start(stub: dict, week_index: int) -> date:
    return date.fromisoformat(stub["periodStart"]) + timedelta(days=7 * week_index)


def _session_for(day: date, calendar: dict) -> dict | None:
    for s in calendar["sessions"]:
        if date.fromisoformat(s["start"]) <= day <= date.fromisoformat(s["end"]):
            return s
    return None


def _fica_part(part: str, field: str, rate_bp: int, label: str, stubs: list[dict]) -> dict | None:
    """One withholding line as its own finding. Confidence drops when the amount isn't the
    statutory rate of gross, since that means we may be misreading the paystub."""
    withheld = [s for s in stubs if s[field] > 0]
    if not withheld:
        return None
    off = [s for s in withheld if abs(s[field] - pct_of(s["grossCents"], rate_bp)) > 1]
    reasons = [f"{label} on {s['periodStart']} is {money(s[field])}, not {rate_bp / 100:.2f}% of gross "
               f"({money(pct_of(s['grossCents'], rate_bp))})" for s in off]
    total = sum(s[field] for s in withheld)
    per = [{"periodStart": s["periodStart"], "periodEnd": s["periodEnd"], "amountCents": s[field],
            "display": money(s[field])} for s in withheld]
    return {
        "part": part,
        "label": label,
        "amountCents": total,
        "display": money(total),
        "confidence": "medium" if off else "high",
        "confidenceReasons": reasons or [f"every {label} amount is exactly {rate_bp / 100:.2f}% of gross"],
        "perPaycheck": per,
    }


def decide_fica_exempt(profile: dict, paystubs: list[dict], calendar: dict, as_of: date) -> Hit | NoFlag:
    """F-1 or J-1 within its exempt calendar years, and Social Security or Medicare was withheld.
    Social Security and Medicare are separate findings with their own confidence."""
    limit = exempt_years(profile)
    if isinstance(limit, NoFlag):
        return limit
    exempt, late = [], []
    for stub in paystubs:
        n = calendar_year_number(profile["arrivalDate"], date.fromisoformat(stub["periodEnd"]).year)
        (exempt if 1 <= n <= limit else late).append((stub, n))
    stubs = [s for s, _ in exempt if s["ssCents"] + s["medicareCents"] > 0]
    if not stubs:
        if late and not exempt:
            n = max(n for _, n in late)
            return NoFlag(f"calendar year {n} on {status_label(profile)} is past the {limit}-year exemption, "
                          "so withholding is likely correct")
        return NoFlag("nothing withheld during exempt years")
    findings = [f for f in (_fica_part("social_security", "ssCents", SS_RATE_BP, "Social Security", stubs),
                            _fica_part("medicare", "medicareCents", MEDICARE_RATE_BP, "Medicare", stubs)) if f]
    per_paycheck = [{"periodStart": s["periodStart"], "periodEnd": s["periodEnd"], "employer": s["employer"],
                     "socialSecurityCents": s["ssCents"], "medicareCents": s["medicareCents"],
                     "totalCents": s["ssCents"] + s["medicareCents"],
                     "display": money(s["ssCents"] + s["medicareCents"])} for s in stubs]
    totals = {p["totalCents"] for p in per_paycheck}
    uniform = per_paycheck[0]["totalCents"] if len(totals) == 1 else None
    ss, medicare = sum(s["ssCents"] for s in stubs), sum(s["medicareCents"] for s in stubs)
    years = sorted({n for s, n in exempt if s in stubs})
    return Hit({
        "amountCents": ss + medicare,
        "ssCents": ss,
        "medicareCents": medicare,
        "basis": F1_NRA_EXEMPT,
        "studentException": student_exception(profile),
        "status": status_label(profile),
        "exemptYears": limit,
        "calendarYears": years,
        "periods": [[s["periodStart"], s["periodEnd"]] for s in stubs],
        "employers": sorted({s["employer"] for s in stubs}),
        "findings": findings,
        "amounts": {
            "totalCents": ss + medicare,
            "socialSecurityCents": ss,
            "medicareCents": medicare,
            "paychecks": len(stubs),
            "perPaycheckCents": uniform,
            "perPaycheck": per_paycheck,
            "display": {
                "total": money(ss + medicare),
                "socialSecurity": money(ss),
                "medicare": money(medicare),
                "perPaycheck": money(uniform) if uniform is not None else None,
            },
        },
    })


def decide_over_20_hours(profile: dict, paystubs: list[dict], calendar: dict, as_of: date) -> Hit | NoFlag:
    """Any week whose start date falls inside a session with hours above 20. Breaks are exempt."""
    weeks = []
    for stub in paystubs:
        for i, hours in enumerate(stub["hoursByWeek"]):
            start = _week_start(stub, i)
            session = _session_for(start, calendar)
            if hours > WEEKLY_HOUR_LIMIT and session:
                weeks.append({"weekStart": start.isoformat(), "hours": hours, "session": session["name"]})
    if not weeks:
        return NoFlag(f"no week over {WEEKLY_HOUR_LIMIT} hours while school was in session")
    return Hit({"amountCents": 0, "weeks": weeks})


def decide_needs_8843(profile: dict, paystubs: list[dict], calendar: dict, as_of: date) -> Hit | NoFlag:
    """An exempt individual last tax year, and no 8843 recorded for it.

    Due April 15 when the student had US wages that year (filed with 1040-NR), otherwise June 15.
    Weekend/holiday shifts are not applied.
    """
    limit = exempt_years(profile)
    if isinstance(limit, NoFlag):
        return limit
    tax_year = as_of.year - 1
    n = calendar_year_number(profile["arrivalDate"], tax_year)
    if n < 1:
        return NoFlag(f"not in the US in {tax_year}")
    if n > limit:
        return NoFlag(f"{tax_year} was calendar year {n}, past the {limit}-year exemption")
    if tax_year in profile.get("filed8843Years", []):
        return NoFlag(f"Form 8843 for {tax_year} already filed")
    had_wages = any(date.fromisoformat(s["periodEnd"]).year == tax_year and s["grossCents"] > 0 for s in paystubs)
    deadline = date(tax_year + 1, 4, 15) if had_wages else date(tax_year + 1, 6, 15)
    return Hit({
        "amountCents": 0,
        "taxYear": tax_year,
        "deadline": deadline.isoformat(),
        "overdue": as_of > deadline,
        "hadWages": had_wages,
    })


def decide_resident_tax_software(profile: dict, paystubs: list[dict], calendar: dict, as_of: date) -> Hit | NoFlag:
    """A nonresident who reports filing with software that only does the resident Form 1040."""
    software = (profile.get("taxSoftware") or "").strip()
    if not software:
        return NoFlag("no tax software reported")
    if software.lower() not in RESIDENT_TAX_SOFTWARE:
        return NoFlag(f"{software} is not on the list of resident-only tax software")
    limit = exempt_years(profile)
    if isinstance(limit, NoFlag):
        return limit
    tax_year = as_of.year - 1
    n = calendar_year_number(profile["arrivalDate"], tax_year)
    if not 1 <= n <= limit:
        return NoFlag(f"{tax_year} was calendar year {n}, so she may not be a nonresident for that return")
    return Hit({"amountCents": 0, "severity": "warning", "software": software, "taxYear": tax_year,
                "expectedForm": "1040-NR"})


def _days(start: date, end: date) -> set[date]:
    return {start + timedelta(days=i) for i in range((end - start).days + 1)}


def decide_opt_unemployment(profile: dict, paystubs: list[dict], calendar: dict, as_of: date) -> Hit | NoFlag:
    """Post-completion OPT: days since the EAD start date with no reported job, against the
    90-day limit. Warns from 60 days. Counts from the student's reported jobs, not pay, since
    status depends on being employed. STEM OPT (150 days) is not covered yet.
    """
    opt = profile.get("opt")
    if not opt:
        return NoFlag("not on OPT")
    if opt.get("type") != "post_completion":
        return NoFlag(f"OPT type {opt.get('type') or 'unknown'} is not covered yet; only post-completion OPT")
    try:
        start = date.fromisoformat(opt["eadStart"])
        end = min(as_of, date.fromisoformat(opt["eadEnd"]))
    except (KeyError, TypeError, ValueError):
        return NoFlag("OPT start or end date unknown")
    if as_of < start:
        return NoFlag(f"OPT starts {start.isoformat()}")
    worked: set[date] = set()
    for job in opt.get("employment", []):
        job_end = date.fromisoformat(job["end"]) if job.get("end") else end
        worked |= _days(max(start, date.fromisoformat(job["start"])), min(end, job_end))
    used = len(_days(start, end) - worked)
    left = OPT_UNEMPLOYMENT_LIMIT - used
    if used < OPT_WARN_AT:
        return NoFlag(f"{used} of {OPT_UNEMPLOYMENT_LIMIT} unemployment days used on OPT")
    employed_now = end in worked
    detail = {
        "amountCents": 0,
        "severity": "warning",
        "daysUsed": used,
        "limit": OPT_UNEMPLOYMENT_LIMIT,
        "daysLeft": max(left, 0),
        "overLimit": used > OPT_UNEMPLOYMENT_LIMIT,
        "employedNow": employed_now,
        "countedThrough": end.isoformat(),
    }
    if not employed_now and left > 0:
        detail["limitReachedOn"] = (end + timedelta(days=left)).isoformat()
    return Hit(detail)


DECISIONS = {
    "fica_exempt": decide_fica_exempt,
    "over_20_hours_in_session": decide_over_20_hours,
    "needs_8843": decide_needs_8843,
    "resident_tax_software": decide_resident_tax_software,
    "opt_unemployment": decide_opt_unemployment,
}


def _yes_no(decide):
    def check(profile: dict, paystubs: list[dict], calendar: dict, as_of: date) -> dict | None:
        result = decide(profile, paystubs, calendar, as_of)
        return result.detail if isinstance(result, Hit) else None
    check.__name__, check.__doc__ = decide.__name__.removeprefix("decide_"), decide.__doc__
    return check


fica_exempt = _yes_no(decide_fica_exempt)
over_20_hours_in_session = _yes_no(decide_over_20_hours)
needs_8843 = _yes_no(decide_needs_8843)
resident_tax_software = _yes_no(decide_resident_tax_software)
opt_unemployment = _yes_no(decide_opt_unemployment)

CHECKS = {name: _yes_no(decide) for name, decide in DECISIONS.items()}
