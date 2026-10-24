from rules.demo_rejection import MADE_UP, demo_rows
from rules.engine import load_rules


def test_made_up_clause_rejected_real_quote_accepted():
    rule = next(r for r in load_rules() if r["id"] == "FICA_EXEMPT_F1")
    source = {"_id": "s1", "title": "IRS Publication 519", "text": f"Students.\n{rule['quote']}\nMore."}
    rows = demo_rows(MADE_UP, rule, source)
    assert [r["action"] for r in rows] == ["quote_rejected", "quote_accepted"]
    assert all(r["agent"] == "tax" and r["sourceId"] == "s1" for r in rows)
    assert "quote not found in stored source" in rows[0]["detail"]
