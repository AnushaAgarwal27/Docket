from rules.quote_checker import check_quote

SOURCE = "Some intro.\n\nServices performed by you  as a nonresident alien are not covered under the “social security” program if conditions are met."


def test_exact_match_with_messy_whitespace_and_curly_quotes():
    q = 'Services performed by you as a nonresident alien are not covered under the "social security" program'
    assert check_quote(q, SOURCE).ok


def test_paraphrase_rejected():
    r = check_quote("Services you perform as a nonresident alien are not covered under social security", SOURCE)
    assert not r.ok and r.reason == "quote not found in stored source"


def test_made_up_clause_rejected():
    assert not check_quote("F-1 students are exempt from all federal taxes for their first five years.", SOURCE).ok


def test_case_matters():
    assert not check_quote("services performed by you as a nonresident alien are not covered", SOURCE).ok


def test_too_short_rejected():
    assert check_quote("not covered", SOURCE).reason.startswith("quote shorter")
