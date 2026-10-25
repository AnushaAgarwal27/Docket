"""Tax and status: run every rule in rules.yaml against one student and write flags.

Rules decide in code. A flag is written only if its quote is found word for word in the
stored source; otherwise the rejection is logged and nothing is shown.
Explanations are fixed templates for now; Claude will phrase them once the key is in.
"""

from datetime import date
from pathlib import Path

import yaml

from agents.store import dollars, log, mutation, query
from rules import rules as checks
from rules.quote_checker import check_quote
from seed.demo_data import SCHOOL_CALENDAR

AGENT = "tax"
RULES_FILE = Path(__file__).resolve().parents[2] / "rules" / "rules.yaml"
DISCLAIMER = "Confirm with your school's international office."


def explain(rule_id: str, hit: dict) -> str:
    if rule_id == "FICA_EXEMPT_F1":
        years = " and ".join(str(n) for n in hit["calendarYears"])
        return (f"You are likely exempt from Social Security and Medicare tax (calendar year {years} "
                f"of {hit.get('exemptYears', 5)} on {hit.get('status', 'F-1')}), but {dollars(hit['amountCents'])} was withheld. "
                f"You can likely get it refunded. {DISCLAIMER}")
    if rule_id == "ONCAMPUS_20_HOURS":
        weeks = "; ".join(f"{w['hours']} hours the week of {w['weekStart']} ({w['session']})" for w in hit["weeks"])
        return f"You likely worked {weeks}, over the 20-hour weekly limit while school is in session. {DISCLAIMER}"
    if rule_id == "FORM_8843_ANNUAL":
        return (f"You likely need to file Form 8843 for {hit['taxYear']}, due {hit['deadline']}, "
                f"even with no income. {DISCLAIMER}")
    if rule_id == "WRONG_TAX_FORM":
        return (f"You likely filed your {hit['taxYear']} return with {hit['software']}, which prepares the resident "
                f"Form 1040. As a nonresident you likely need Form {hit['expectedForm']} instead. {DISCLAIMER}")
    if rule_id == "OPT_UNEMPLOYMENT":
        if hit["overLimit"]:
            return (f"You have likely used {hit['daysUsed']} days of unemployment on OPT, over the {hit['limit']}-day "
                    f"limit, which can affect your F-1 status. {DISCLAIMER}")
        until = f" If you stay unemployed, you reach the limit on {hit['limitReachedOn']}." if "limitReachedOn" in hit else ""
        return (f"You have likely used {hit['daysUsed']} of {hit['limit']} unemployment days on OPT, "
                f"{hit['daysLeft']} left.{until} {DISCLAIMER}")
    raise ValueError(f"no explanation template for {rule_id}")


def paystub_ids(hit: dict, paystubs: list[dict]) -> list[str]:
    """The paystubs a rule hit on, read from the rule's own result (pay periods, or the weeks over the limit)."""
    starts = {start for start, _ in hit.get("periods", [])}
    weeks = [w["weekStart"] for w in hit.get("weeks", [])]
    return [p["_id"] for p in paystubs
            if p["periodStart"] in starts or any(p["periodStart"] <= w <= p["periodEnd"] for w in weeks)]


def rules_profile(profile: dict) -> dict:
    """The student file stores the employer as a name plus employmentType / employerIsSchool; the rules
    (rules/rules.py) read it as {"name", "type": "university" | "contractor"}. Translate, never guess."""
    employer = profile.get("employer")
    if isinstance(employer, dict) or employer is None:
        return profile
    kind = ("contractor" if profile.get("employmentType") == "contractor"
            else "university" if profile.get("employerIsSchool") else None)
    return {**profile, "employer": {"name": employer, **({"type": kind} if kind else {})}}


def run(profile_id: str, as_of: date | None = None, calendar: dict = SCHOOL_CALENDAR) -> list[dict]:
    """Returns the flags written this run, as stored rows. The calendar lets the rules skip breaks."""
    as_of = as_of or date.today()
    profile = query("profiles:get", {"profileId": profile_id})
    if profile is None:
        return []  # the student file was reset
    paystubs = query("paystubs:listByProfile", {"profileId": profile_id})
    written = []

    for rule in yaml.safe_load(RULES_FILE.read_text()):
        hit = checks.CHECKS[rule["check"]](rules_profile(profile), paystubs, calendar, as_of)
        if hit is None:
            log(AGENT, "rule_not_triggered", f"{rule['id']}: no issue for {profile['name']}", inputIds=[profile_id])
            continue

        source = query("sources:getByUrl", {"url": rule["source_url"]})
        if source is None:
            log(AGENT, "flag_blocked", f"{rule['id']}: source not fetched yet ({rule['source_url']})")
            continue
        result = check_quote(rule["quote"], source["text"])
        if not result.ok:
            log(AGENT, "quote_rejected", f"{rule['id']}: {result.reason}",
                sourceId=source["_id"])
            continue

        flag_id = mutation("flags:upsert", {
            "profileId": profile_id,
            "ruleId": rule["id"],
            "amountCents": hit["amountCents"],
            "explanation": explain(rule["id"], hit),
            "quote": rule["quote"],
            "sourceId": source["_id"],
            "status": "contested",  # until the Hearing's verdict sets it (a re-run keeps the status it has)
            "paystubIds": paystub_ids(hit, paystubs),
            # The rule's own totals, so letters quote them instead of re-adding paystubs.
            **{k: hit[k] for k in ("ssCents", "medicareCents") if k in hit},
        })
        log(AGENT, "flag_written", f"{rule['id']}: {dollars(hit['amountCents'])}" if hit["amountCents"] else rule["id"],
            sourceId=source["_id"], inputIds=[profile_id], outputIds=[flag_id])
        written.append({**rule, "flagId": flag_id, "hit": hit, "explanation": explain(rule["id"], hit),
                        "sourceTitle": source["title"], "sourceId": source["_id"]})
    return written
