"""Read a card selection out of a chat message.

ASI:One returns a card click two ways (Interactive Cards docs): as a JSON object string when the student
@mentions the agent directly, or as a prose sentence when ASI:One's planner relays it. In prose, every
identifier from the card's selection appears in the sentence. So: try JSON first, then look for our own
action ids and field names in the text.
"""
from __future__ import annotations

import json
import re

# Every `selection.action` value Docket's cards use. Prose is matched only against these.
ACTIONS = ("approve_refund", "decline_refund", "submit_profile", "show_hearing")
# Form fields whose values can be read back from prose ("arrival_date: 2024-08-15").
FIELDS = ("arrival_date", "visa_type", "employer", "employment_type")


def parse_selection(text: str) -> dict | None:
    """The selection as a dict with an "action" key, or None if the message is not a card selection."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        data = None
    if isinstance(data, dict):
        return data if data.get("action") in ACTIONS else None
    return _from_prose(text)


def _from_prose(text: str) -> dict | None:
    found = [a for a in ACTIONS if re.search(rf"\b{a}\b", text)]
    if len(found) != 1:
        return None  # none, or ambiguous: never guess which button was pressed
    selection = {"action": found[0]}
    for field in FIELDS:
        m = re.search(rf"\b{field}\b\s*(?:[:=]|\bis\b|\bof\b)\s*[\"']?([^,;\n\"']+?)[\"']?\s*(?=[,;\n.]|\band\b|$)", text)
        if m:
            selection[field] = m.group(1).strip()
    return selection
