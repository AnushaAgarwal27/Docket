"""The forms Docket fills in, each built from stored values only.

Every entry in `fields` is (label, value, source), where `source` names the record the value was
read from. Nothing here computes a new number: totals come from the flag the rules engine wrote,
dates come from the paystubs, and the student's details come from her profile. If a value is
missing, the form says so and is not submitted — it is never filled with a plausible guess.

The forms:
    form_8843       Statement for Exempt Individuals. Every F-1 student files one every year, with
                    or without income. This is the most common thing students do not know about.
    form_843        Claim for Refund and Request for Abatement. The IRS route for FICA withheld in
                    error, used when the employer will not refund it.
    form_8316       The statement that goes with Form 843: the employer refused, here is why.
    refund_letter   The written request to the employer, used before the IRS route.
"""
from __future__ import annotations

from datetime import date

from agents.store import dollars

DISCLAIMER = "This is not tax advice; confirm with your international student office before filing."


class MissingFact(RuntimeError):
    """A value the form needs is not on file. The form is not filled in with a guess."""


def need(profile: dict, key: str, label: str):
    value = profile.get(key)
    if value in (None, "", []):
        raise MissingFact(f"{label} is not on your file yet")
    return value


def tax_year(today: date) -> int:
    """Forms filed in a year cover the year before it."""
    return today.year - 1


def years_in_us(profile: dict, year: int) -> int:
    return year - int(str(profile["arrivalDate"])[:4]) + 1


# ---------------------------------------------------------------------------

def form_8843(profile: dict, paystubs: list[dict], flag: dict | None, today: date) -> dict:
    year = tax_year(today)
    name = need(profile, "name", "Your name")
    arrival = need(profile, "arrivalDate", "Your arrival date")
    visa = need(profile, "visa", "Your visa type")
    school = profile.get("school") or "your school"
    fields = [
        ("Tax year", str(year), "computed from today's date"),
        ("Name", name, "profiles.name"),
        ("Visa type", visa, "profiles.visa"),
        ("Date first entered the US", str(arrival), "profiles.arrivalDate"),
        ("Calendar year in the US", f"{years_in_us(profile, year)} of 5", "computed from profiles.arrivalDate"),
        ("Academic institution", school, "profiles.school"),
        ("Days present in the US in " + str(year), "all year unless you were abroad",
         "not tracked by Docket; confirm before filing"),
    ]
    body = (
        f"Form 8843, Statement for Exempt Individuals and Individuals With a Medical Condition\n"
        f"Tax year {year}\n\n"
        f"{name}, {visa} student at {school}, first entered the United States on {arrival}. "
        f"{year} is calendar year {years_in_us(profile, year)} of the 5 years an F-1 student is "
        f"normally treated as an exempt individual, so her days in the United States are not counted "
        f"toward the substantial presence test for {year}.\n\n"
        f"Every F-1 student must file Form 8843 for each year they are in the United States, whether "
        f"or not they earned any income and whether or not they file a tax return. Filing it is how "
        f"the exemption above is claimed.\n\n"
        f"Before filing, check the number of days you were physically present in the United States "
        f"during {year}; Docket does not track your travel.\n\n{DISCLAIMER}"
    )
    return {"kind": "form_8843", "title": f"Form 8843 for {year}", "submitTo": "IRS",
            "fields": fields, "body": body}


def form_843(profile: dict, paystubs: list[dict], flag: dict | None, today: date) -> dict:
    if flag is None:
        raise MissingFact("there is no refund finding on your file to claim")
    name = need(profile, "name", "Your name")
    linked = [p for p in paystubs if p["_id"] in set(flag.get("paystubIds") or [])] or paystubs
    if not linked:
        raise MissingFact("no paystubs are linked to the finding")
    employer = linked[0]["employer"]
    first, last = min(p["periodStart"] for p in linked), max(p["periodEnd"] for p in linked)
    year = int(str(last)[:4])
    ss, medicare = flag.get("ssCents"), flag.get("medicareCents")
    if ss is None or medicare is None:
        raise MissingFact("the Social Security and Medicare totals are not on the finding yet")
    fields = [
        ("Tax year of the claim", str(year), "paystubs.periodEnd"),
        ("Name", name, "profiles.name"),
        ("Employer who withheld", employer, "paystubs.employer"),
        ("Social Security withheld", dollars(ss), "flags.ssCents"),
        ("Medicare withheld", dollars(medicare), "flags.medicareCents"),
        ("Total claimed", dollars(flag["amountCents"]), "flags.amountCents"),
        ("Pay periods", f"{first} to {last}", "paystubs.periodStart / periodEnd"),
        ("Reason for the claim", "Social Security and Medicare tax withheld from a nonresident alien "
                                 "student exempt under IRC 3121(b)(19)", "rules engine"),
    ]
    body = (
        f"Form 843, Claim for Refund and Request for Abatement\n"
        f"Tax year {year}\n\n"
        f"{name} is a nonresident alien student in {profile.get('visa', 'F-1')} status. "
        f"{employer} withheld Social Security tax of {dollars(ss)} and Medicare tax of "
        f"{dollars(medicare)}, a total of {dollars(flag['amountCents'])}, from {len(linked)} "
        f"paychecks covering {first} to {last}.\n\n"
        f"Services performed by a nonresident alien student in F-1 status are excepted from Social "
        f"Security and Medicare tax. The employer was asked to refund the amounts and did not do so, "
        f"so this claim is made to the IRS directly.\n\n"
        f"Attach to this form: Form 8316, your W-2, your visa, Form I-94, Form I-20, and the "
        f"employer's written statement (or a note explaining that you could not obtain one).\n\n"
        f"{DISCLAIMER}"
    )
    return {"kind": "form_843", "title": f"Form 843 claim for {year}", "submitTo": "IRS",
            "fields": fields, "body": body}


def form_8316(profile: dict, paystubs: list[dict], flag: dict | None, today: date) -> dict:
    if flag is None:
        raise MissingFact("there is no refund finding on your file to claim")
    name = need(profile, "name", "Your name")
    linked = [p for p in paystubs if p["_id"] in set(flag.get("paystubIds") or [])] or paystubs
    if not linked:
        raise MissingFact("no paystubs are linked to the finding")
    employer = linked[0]["employer"]
    year = int(str(max(p["periodEnd"] for p in linked))[:4])
    fields = [
        ("Tax year", str(year), "paystubs.periodEnd"),
        ("Name", name, "profiles.name"),
        ("Employer who withheld", employer, "paystubs.employer"),
        ("Amount withheld in error", dollars(flag["amountCents"]), "flags.amountCents"),
        ("Did the employer refund it?", "No", "cases.outcome"),
    ]
    body = (
        f"Form 8316, Information Regarding Request for Refund of Social Security Tax Erroneously "
        f"Withheld on Wages Received by a Nonresident Alien on an F, J, or M Type Visa\n"
        f"Tax year {year}\n\n"
        f"{name} asked {employer} to refund the {dollars(flag['amountCents'])} of Social Security and "
        f"Medicare tax withheld from her pay in error. The employer did not refund it. She has not "
        f"claimed, and will not claim, a refund or credit of this amount from any other source.\n\n"
        f"This statement accompanies her Form 843 claim.\n\n{DISCLAIMER}"
    )
    return {"kind": "form_8316", "title": f"Form 8316 statement for {year}", "submitTo": "IRS",
            "fields": fields, "body": body}


def refund_letter(profile: dict, paystubs: list[dict], flag: dict | None, today: date) -> dict:
    if flag is None:
        raise MissingFact("there is no refund finding on your file")
    name = need(profile, "name", "Your name")
    linked = [p for p in paystubs if p["_id"] in set(flag.get("paystubIds") or [])] or paystubs
    if not linked:
        raise MissingFact("no paystubs are linked to the finding")
    employer = linked[0]["employer"]
    first, last = min(p["periodStart"] for p in linked), max(p["periodEnd"] for p in linked)
    ss, medicare = flag.get("ssCents"), flag.get("medicareCents")
    if ss is None or medicare is None:
        raise MissingFact("the Social Security and Medicare totals are not on the finding yet")
    fields = [
        ("To", f"{employer} payroll", "paystubs.employer"),
        ("From", name, "profiles.name"),
        ("Social Security withheld", dollars(ss), "flags.ssCents"),
        ("Medicare withheld", dollars(medicare), "flags.medicareCents"),
        ("Total requested", dollars(flag["amountCents"]), "flags.amountCents"),
        ("Pay periods", f"{first} to {last}", "paystubs.periodStart / periodEnd"),
    ]
    quote = flag.get("quote")
    body = (
        f"{today.strftime('%B %-d, %Y')}\n\n"
        f"To: {employer} Payroll\n"
        f"Re: Refund of Social Security and Medicare withheld in error, {name}\n\n"
        f"{name} is a nonresident alien student in {profile.get('visa', 'F-1')} status. Social "
        f"Security ({dollars(ss)}) and Medicare ({dollars(medicare)}) were withheld from "
        f"{len(linked)} paychecks for pay periods {first} to {last}, a total of "
        f"{dollars(flag['amountCents'])}.\n\n"
        + (f'The IRS states: "{quote}"\n\n' if quote else "")
        + f"Please refund {dollars(flag['amountCents'])} and stop withholding these taxes from her "
        f"future paychecks. If you cannot refund it, please provide a written statement saying so, "
        f"so she can claim it from the IRS.\n\n"
        f"Sent by {name}, prepared with Docket.\n\n{DISCLAIMER}"
    )
    return {"kind": "refund_letter", "title": f"Refund request to {employer}",
            "submitTo": f"{employer} payroll", "fields": fields, "body": body}


BUILDERS = {
    "form_8843": form_8843,
    "form_843": form_843,
    "form_8316": form_8316,
    "refund_letter": refund_letter,
}


def build(kind: str, profile: dict, paystubs: list[dict], flag: dict | None,
          today: date | None = None) -> dict:
    builder = BUILDERS.get(kind)
    if builder is None:
        raise MissingFact(f"Docket does not know how to fill in {kind}")
    return builder(profile, paystubs, flag, today or date.today())
