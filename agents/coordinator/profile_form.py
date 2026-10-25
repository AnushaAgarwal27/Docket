"""Reading the profile form card back into the student file. Every value is checked in code first."""
from __future__ import annotations

import re
from datetime import date

TRUE = {"true", "yes", "on", "1", "checked"}
FALSE = {"false", "no", "off", "0", "unchecked", ""}


def _bool(value) -> bool | None:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return True if text in TRUE else False if text in FALSE else None


def form_changes(selection: dict, today: date) -> tuple[dict, list[str]]:
    """(profile fields to write, problems). Fields the student left out are not touched."""
    changes, problems = {}, []
    arrival = str(selection.get("arrival_date", "")).strip()
    if arrival:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", arrival):
            try:
                d = date.fromisoformat(arrival)
            except ValueError:
                d = None
            if d is None or d > today or d.year < 1950:
                problems.append("arrival date must be a real date, not in the future")
            else:
                changes["arrivalDate"] = arrival
        else:
            problems.append("arrival date must look like 2024-08-15")
    visa = str(selection.get("visa_type", "")).strip().upper()
    if visa:
        changes["visa"] = visa if visa in ("F-1", "J-1") else "other"
    employer = str(selection.get("employer", "")).strip()
    if employer:
        changes["employer"] = employer[:120]
    kind = str(selection.get("employment_type", "")).strip().lower()
    if kind:
        if kind in ("employee", "contractor"):
            changes["employmentType"] = kind
        else:
            problems.append("employment type must be employee or contractor")
    for field, key in (("employer_is_school", "employerIsSchool"), ("enrolled", "enrolled")):
        if field in selection:
            value = _bool(selection[field])
            if value is None:
                problems.append(f"{field.replace('_', ' ')} must be yes or no")
            else:
                changes[key] = value
    return changes, problems
