"""The Auditor's side of the Hearing: every reason a claim might be wrong, checked in code.

Each objection is {id, severity, part, evidence_ids, message_facts}. Severity says what the objection
does if the Advocate cannot answer it: "fatal" defeats the claim, "downgrade" lowers confidence so the
student decides, "missing" means facts are missing so a person must check. `part` is "social_security",
"medicare" or "both" for the FICA claim. message_facts hold only stored or computed facts, never prose
from a model.
"""
from __future__ import annotations

FICA = "FICA_EXEMPT_F1"
HOURS = "ONCAMPUS_20_HOURS"


def objection(oid: str, severity: str, part: str, evidence: list[str], **facts) -> dict:
    return {"id": oid, "severity": severity, "part": part, "evidence_ids": evidence, "message_facts": facts}


def objections(claim: dict, profile: dict) -> list[dict]:
    """The objections the Auditor raises against `claim` (built by the Advocate from the student file)."""
    if claim["rule_id"] == HOURS:
        return [objection("school_in_session", "fatal", "both", claim["paystub_ids"],
                          weeks=claim["weeks"])]
    if claim["rule_id"] != FICA:
        return []
    profile_ref = [profile["_id"]] if profile.get("_id") else []
    found = []
    if not profile.get("visa") or not profile.get("arrivalDate"):
        found.append(objection("missing_visa_or_arrival_data", "missing", "both", profile_ref,
                               visa=profile.get("visa"), arrival_date=profile.get("arrivalDate")))
        return found  # nothing else can be judged without these
    found.append(objection("employer_is_contractor", "missing", "both", profile_ref,
                           employer=claim["employer"], employment_type=profile.get("employmentType")))
    found.append(objection("year_count_boundary", "fatal", "both", profile_ref + claim["paystub_ids"],
                           arrival_date=profile["arrivalDate"], calendar_years=claim["calendar_years"],
                           exempt_years=5))
    if profile.get("employerIsSchool") and profile.get("enrolled"):
        found.append(objection("student_exception_applies", "downgrade", "both", profile_ref,
                               employer=claim["employer"]))
    if claim["medicare_cents"] > 0:
        found.append(objection("medicare_recovery_uncertain", "downgrade", "medicare", claim["paystub_ids"],
                               medicare_cents=claim["medicare_cents"]))
    return found


def argument(obj: dict) -> str:
    """The Auditor's objection as one sentence, from its facts."""
    f, oid = obj["message_facts"], obj["id"]
    if oid == "missing_visa_or_arrival_data":
        return "The student file is missing the visa type or arrival date, so the exemption can't be checked."
    if oid == "employer_is_contractor":
        return (f"If {f['employer']} treats this as contractor work, the payroll rules for employees "
                f"wouldn't apply at all.")
    if oid == "year_count_boundary":
        years = " and ".join(map(str, f["calendar_years"])) or "unknown"
        return (f"The exemption only lasts {f['exempt_years']} calendar years. These paychecks are from calendar "
                f"year {years}, counting from arrival on {f['arrival_date']}.")
    if oid == "student_exception_applies":
        return (f"{f['employer']} is the student's own school. A different exemption, the student exception, may be "
                f"the right basis instead of the F-1 rule.")
    if oid == "medicare_recovery_uncertain":
        return "Medicare is treated differently from Social Security, and some employers won't refund it."
    if oid == "school_in_session":
        return "The 20-hour limit only applies while school is in session. Was that week a break?"
    return oid.replace("_", " ")
