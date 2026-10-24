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
                f"of 5 on F-1), but {dollars(hit['amountCents'])} was withheld. You can likely get it refunded. {DISCLAIMER}")
    if rule_id == "ONCAMPUS_20_HOURS":
        weeks = "; ".join(f"{w['hours']} hours the week of {w['weekStart']} ({w['session']})" for w in hit["weeks"])
        return f"You likely worked {weeks}, over the 20-hour weekly limit while school is in session. {DISCLAIMER}"
    if rule_id == "FORM_8843_ANNUAL":
        return (f"You likely need to file Form 8843 for {hit['taxYear']}, due {hit['deadline']}, "
                f"even with no income. {DISCLAIMER}")
    raise ValueError(f"no explanation template for {rule_id}")


def run(profile_id: str, as_of: date | None = None, calendar: dict = SCHOOL_CALENDAR) -> list[dict]:
    """Returns the flags written this run, as stored rows. The calendar lets the rules skip breaks."""
    as_of = as_of or date.today()
    profile = query("profiles:get", {"profileId": profile_id})
    paystubs = query("paystubs:listByProfile", {"profileId": profile_id})
    written = []

    for rule in yaml.safe_load(RULES_FILE.read_text()):
        hit = checks.CHECKS[rule["check"]](profile, paystubs, calendar, as_of)
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
            "status": "open",
        })
        log(AGENT, "flag_written", f"{rule['id']}: {dollars(hit['amountCents'])}" if hit["amountCents"] else rule["id"],
            sourceId=source["_id"], inputIds=[profile_id], outputIds=[flag_id])
        written.append({**rule, "flagId": flag_id, "hit": hit, "explanation": explain(rule["id"], hit),
                        "sourceTitle": source["title"]})
    return written
