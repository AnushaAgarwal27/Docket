from agents.coordinator.brain import Finding, Reply, allowed_amounts, problems

FACTS = {
    "paystubs": [{"grossCents": 72000, "ssCents": 4464, "medicareCents": 1044}],
    "ruleResults": [{"ruleId": "FICA_EXEMPT_F1", "amountCents": 44064,
                     "detail": {"ssCents": 35712, "medicareCents": 8352}}],
}
FIRED = {"FICA_EXEMPT_F1"}
SOURCES = {"FICA_EXEMPT_F1": "Social security and Medicare taxes are not withheld from pay for the work "
                             "unless the student is considered a resident alien."}


def reply(message: str, findings=None) -> Reply:
    return Reply(intent="check_pay", needs_human=False, message_to_student=message,
                 findings=findings if findings is not None else
                 [Finding(rule="FICA_EXEMPT_F1", part=None, confidence="high", basis="year 3 of 5", source_quote_id="FICA_EXEMPT_F1")])


def test_amounts_come_from_cents_fields():
    assert {"440.64", "357.12", "83.52", "720.00", "44.64", "10.44"} <= allowed_amounts(FACTS)


def test_clean_reply_passes():
    assert problems(reply("$440.64 was withheld: $357.12 Social Security and $83.52 Medicare."), FACTS, FIRED, SOURCES) == []


def test_amount_the_model_computed_is_rejected():
    # $55.08 per paycheck is arithmetic on the facts, not a fact.
    assert problems(reply("You lose $55.08 every paycheck."), FACTS, FIRED, SOURCES) == ["amount $55.08 is not in the facts"]


def test_social_security_and_medicare_split_is_allowed():
    split = [Finding(rule="FICA_EXEMPT_F1", part="social_security", confidence="high", basis="b", source_quote_id="FICA_EXEMPT_F1"),
             Finding(rule="FICA_EXEMPT_F1", part="medicare", confidence="medium", basis="b", source_quote_id="FICA_EXEMPT_F1")]
    assert problems(reply("ok", split), FACTS, FIRED, SOURCES) == []


def test_rule_that_did_not_fire_is_rejected():
    extra = [Finding(rule="FORM_8843_ANNUAL", part=None, confidence="high", basis="b", source_quote_id=None)]
    assert problems(reply("ok", extra), FACTS, FIRED, SOURCES) == ["finding names a rule that did not fire: FORM_8843_ANNUAL"]


def test_made_up_quote_is_rejected():
    msg = 'The IRS says "students on F-1 visas never pay any federal tax for five years at all."'
    assert problems(reply(msg), FACTS, FIRED, SOURCES) == ["quoted text not found in a verified source"]


def test_real_quote_passes():
    msg = 'The IRS says "Social security and Medicare taxes are not withheld from pay for the work unless the student is considered a resident alien."'
    assert problems(reply(msg), FACTS, FIRED, SOURCES) == []
