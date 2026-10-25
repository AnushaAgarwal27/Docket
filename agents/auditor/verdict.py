"""The verdict, decided in code from the objections and the Advocate's answers.

  defeated     an objection the claim cannot survive was conceded (e.g. past the 5-year exemption)
  needs_human  an objection is unresolved (missing or conflicting facts)
  downgraded   an exception may apply to part or all of the claim, so the student decides
  upheld       every objection was rebutted

FICA is judged per part (Social Security, Medicare), because recovery differs between them.
"""
from __future__ import annotations

PARTS = ("social_security", "medicare")
PART_LABEL = {"social_security": "Social Security", "medicare": "Medicare"}
OBJECTION_LABEL = {
    "missing_visa_or_arrival_data": "Missing visa or arrival date",
    "employer_is_contractor": "Is the employer treating this as contractor work?",
    "year_count_boundary": "Is the student past the 5-year exemption?",
    "student_exception_applies": "Does a different exemption (the student exception) apply instead?",
    "medicare_recovery_uncertain": "Can Medicare actually be recovered?",
    "school_in_session": "Was school in session that week?",
}


def decide(claim: dict, objections: list[dict], rebuttals: list[dict]) -> dict:
    """{verdict, reason, parts: {part: verdict}} for one claim."""
    outcome = {r["objection_id"]: r["outcome"] for r in rebuttals}
    by_id = {o["id"]: o for o in objections}
    fatal = [o for o in objections if o["severity"] == "fatal" and outcome.get(o["id"]) == "conceded"]
    unresolved = [o for o in objections if outcome.get(o["id"], "unresolved") == "unresolved"]
    if fatal:
        return {"verdict": "defeated", "parts": {p: "defeated" for p in PARTS},
                "reason": f"The Auditor wins: {OBJECTION_LABEL.get(fatal[0]['id'], fatal[0]['id'])} Conceded."}
    if unresolved:
        what = "; ".join(OBJECTION_LABEL.get(o["id"], o["id"]) for o in unresolved)
        return {"verdict": "needs_human", "parts": {p: "needs_human" for p in PARTS},
                "reason": f"Facts are missing or conflict: {what}"}
    parts = {p: "upheld" for p in PARTS}
    for oid, result in outcome.items():
        obj = by_id.get(oid)
        if obj and result == "conceded" and obj["severity"] == "downgrade":
            for p in (PARTS if obj["part"] == "both" else (obj["part"],)):
                parts[p] = "downgraded"
    if claim["rule_id"] != "FICA_EXEMPT_F1":
        return {"verdict": "upheld", "parts": {}, "reason": "Every objection was rebutted."}
    if all(v == "upheld" for v in parts.values()):
        return {"verdict": "upheld", "parts": parts, "reason": "Every objection was rebutted."}
    exceptions = [PART_LABEL[p] for p, v in parts.items() if v == "downgraded"]
    return {"verdict": "downgraded", "parts": parts,
            "reason": f"An exception may apply to {' and '.join(exceptions)}, so the student decides whether to go ahead."}


def verdict_line(verdict: dict) -> str:
    """One line for cards and chat, e.g. 'Social Security upheld; Medicare downgraded'."""
    if verdict["verdict"] in ("defeated", "needs_human") or not verdict.get("parts"):
        return {"defeated": "No claim: the Auditor won", "needs_human": "Needs a person to check",
                "upheld": "Upheld", "downgraded": "Downgraded"}[verdict["verdict"]]
    return "; ".join(f"{PART_LABEL[p]} {v}" for p, v in verdict["parts"].items())
