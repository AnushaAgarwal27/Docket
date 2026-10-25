"""The Advocate's side of the Hearing (the Tax agent): build each claim from the student file, and
answer each of the Auditor's objections from the facts: rebutted, conceded or unresolved. All in code;
every sentence is a template filled with stored or computed facts.
"""
from __future__ import annotations

from datetime import date

from agents.store import dollars
from rules.engine import load_rules
from rules.quote_checker import check_quote
from rules.rules import EXEMPT_CALENDAR_YEARS, calendar_year_number

FICA = "FICA_EXEMPT_F1"
HOURS = "ONCAMPUS_20_HOURS"


def rule(rule_id: str) -> dict:
    return next(r for r in load_rules() if r["id"] == rule_id)


def fica_claim(profile: dict, paystubs: list[dict], flag: dict | None, hit: dict | None,
               source: dict | None) -> dict | None:
    """The FICA claim. From the rule's own result when it fired; otherwise Tax still argues for any F-1
    student with Social Security or Medicare withheld (the Auditor can defeat it)."""
    if profile.get("visa") != "F-1":
        return None
    if hit:
        starts = {s for s, _ in hit["periods"]}
        stubs = [p for p in paystubs if p["periodStart"] in starts]
        ss, medicare, amount = hit["ssCents"], hit["medicareCents"], hit["amountCents"]
    else:
        stubs = [p for p in paystubs if p["ssCents"] + p["medicareCents"] > 0]
        if not stubs:
            return None
        ss = sum(p["ssCents"] for p in stubs)
        medicare = sum(p["medicareCents"] for p in stubs)
        amount = ss + medicare
    years = sorted({calendar_year_number(profile["arrivalDate"], date.fromisoformat(p["periodEnd"]).year)
                    for p in stubs}) if profile.get("arrivalDate") else []
    r = rule(FICA)
    quote_ok = bool(source) and check_quote(r["quote"], source["text"]).ok
    return {
        "rule_id": FICA, "flag_id": flag["_id"] if flag else "", "rule_fired": bool(hit),
        "employer": stubs[0]["employer"], "paystub_ids": [p["_id"] for p in stubs], "paystub_count": len(stubs),
        "ss_cents": ss, "medicare_cents": medicare, "amount_cents": amount, "calendar_years": years,
        "quote": r["quote"] if quote_ok else None, "source_title": r["source_title"],
        "source_id": source["_id"] if quote_ok else None,
    }


def hours_claim(flag: dict, hit: dict, paystub_ids: list[str]) -> dict:
    r = rule(HOURS)
    return {"rule_id": HOURS, "flag_id": flag["_id"], "rule_fired": True, "paystub_ids": paystub_ids,
            "weeks": hit["weeks"], "quote": flag["quote"], "source_title": r["source_title"],
            "source_id": flag["sourceId"], "amount_cents": 0}


def opening(claim: dict, profile: dict) -> str:
    """The Advocate's opening argument."""
    if claim["rule_id"] == HOURS:
        w = claim["weeks"][0]
        return (f"{profile['name']} worked {w['hours']} hours the week of {w['weekStart']}, over the 20-hour "
                f"weekly limit for on-campus work while school is in session.")
    years = " and ".join(str(y) for y in claim["calendar_years"]) or "an unknown year"
    return (f"{dollars(claim['ss_cents'])} of Social Security and {dollars(claim['medicare_cents'])} of Medicare "
            f"({dollars(claim['amount_cents'])} in total) were withheld from {claim['paystub_count']} paychecks from "
            f"{claim['employer']}. {profile['name']} is on an F-1 visa, in calendar year {years} in the US, so these "
            f"taxes are likely not owed.")


def rebut(obj: dict, claim: dict, profile: dict) -> dict:
    """The Advocate's answer to one objection: {objection_id, outcome, argument, evidence_ids}."""
    f, oid = obj["message_facts"], obj["id"]

    def answer(outcome: str, argument: str, evidence: list[str] | None = None) -> dict:
        return {"objection_id": oid, "outcome": outcome, "argument": argument,
                "evidence_ids": evidence if evidence is not None else obj["evidence_ids"]}

    if oid == "missing_visa_or_arrival_data":
        return answer("unresolved", "Without the visa type and arrival date in the student file, I can't show "
                                    "the exemption applies.")
    if oid == "employer_is_contractor":
        if f["employment_type"] == "employee":
            return answer("rebutted", f"{profile['name']} is on {f['employer']}'s payroll as an employee, not a "
                                      f"contractor, and the paystubs show taxes withheld by the employer.")
        if f["employment_type"] == "contractor":
            return answer("unresolved", "The student file says contractor, but the paystubs show payroll "
                                        "withholding. Those facts conflict; a person needs to check.")
        return answer("unresolved", "The student file doesn't say whether this job is employee or contractor work.")
    if oid == "year_count_boundary":
        years = f["calendar_years"]
        if years and max(years) <= f["exempt_years"]:
            last = date.fromisoformat(f["arrival_date"]).year + f["exempt_years"] - 1
            return answer("rebutted", f"Every claimed paycheck is from calendar year {' or '.join(map(str, years))} "
                                      f"of {f['exempt_years']}; the exemption runs through {last}.")
        if years and min(years) > f["exempt_years"]:
            return answer("conceded", f"Conceded: these paychecks are from calendar year "
                                      f"{' and '.join(map(str, years))}, past the {f['exempt_years']}-year exemption, "
                                      f"so withholding them is likely correct.")
        return answer("conceded", "Conceded in part: some paychecks are past the 5-year exemption.")
    if oid == "student_exception_applies":
        years = claim["calendar_years"]
        if years and max(years) <= EXEMPT_CALENDAR_YEARS:
            return answer("rebutted", "The F-1 nonresident rule covers this on its own, so the claim doesn't depend "
                                      "on the student exception; that would only be a second reason.")
        return answer("conceded", "Conceded: past year 5 the claim would rest on the student exception alone, "
                                  "which payroll has to confirm.")
    if oid == "medicare_recovery_uncertain":
        return answer("conceded", "Agreed: Medicare refunds are handled differently from employer to employer, so "
                                  "Medicare is a separate, less certain part of the claim.")
    if oid == "school_in_session":
        sessions = sorted({w["session"] for w in f["weeks"]})
        return answer("rebutted", f"The school calendar puts the week of {f['weeks'][0]['weekStart']} inside "
                                  f"{', '.join(sessions)}, so the 20-hour limit applied.")
    return answer("unresolved", "I have no answer to this objection in the student file.")
