from agents.coordinator.brain import Finding, Reply
from agents.coordinator.intents import NOT_ADVICE, compose

FLAGS = [
    {"ruleId": "FICA_EXEMPT_F1", "quote": "Social security and Medicare taxes are not withheld", "title": "IRS Pub 519",
     "url": "https://www.irs.gov/publications/p519"},
    {"ruleId": "ONCAMPUS_20_HOURS", "quote": "must not exceed 20 hours a week while school is in session",
     "title": "8 CFR 214.2", "url": "https://www.ecfr.gov"},
]


def reply(*cited: str | None) -> Reply:
    return Reply(intent="check_pay", needs_human=False, message_to_student="Here is what I found.",
                 findings=[Finding(rule="FICA_EXEMPT_F1", part=None, confidence="high", basis="b", source_quote_id=c)
                           for c in cited])


def test_only_cited_quotes_are_inserted_once_each():
    out = compose(reply("FICA_EXEMPT_F1", "FICA_EXEMPT_F1"), FLAGS, [])
    assert out.count("> Social security and Medicare taxes are not withheld") == 1
    assert "20 hours" not in out


def test_unknown_or_missing_ids_insert_nothing():
    out = compose(reply("MADE_UP", None), FLAGS, [])
    assert "> " not in out


def test_disclaimer_is_always_last():
    out = compose(reply("FICA_EXEMPT_F1"), FLAGS, ["Reply **YES** to approve."])
    assert out.endswith(NOT_ADVICE) and out.count(NOT_ADVICE) == 1
