from seed import demo_data as d


def test_every_paystub_matches_plan_table():
    stubs = d.paystubs()
    assert len(stubs) == 8
    for s in stubs:
        assert (s["grossCents"], s["ssCents"], s["medicareCents"], s["netCents"]) == (72000, 4464, 1044, 66492)
        assert sum(s["hoursByWeek"]) == 40


def test_totals_and_hero_number():
    stubs = d.paystubs()
    assert sum(s["grossCents"] for s in stubs) == 576000
    assert sum(s["ssCents"] for s in stubs) == 35712
    assert sum(s["medicareCents"] for s in stubs) == 8352
    assert sum(s["netCents"] for s in stubs) == 531936
    assert sum(s["ssCents"] + s["medicareCents"] for s in stubs) == d.REFUND_CENTS == 44064


def test_only_paystub_5_splits_16_24():
    assert [s["hoursByWeek"] for s in d.paystubs()][4] == [16, 24]
    assert sum(s["hoursByWeek"] != [20, 20] for s in d.paystubs()) == 1


def test_deposits_land_one_or_two_days_after_period():
    from datetime import date
    for stub, dep in zip(d.paystubs(), d.payroll_deposits()):
        lag = (date.fromisoformat(dep["date"]) - date.fromisoformat(stub["periodEnd"])).days
        assert lag in (1, 2) and dep["amountCents"] == stub["netCents"]
        assert dep["counterparty"] == "University Dining Payroll"


def test_transaction_mix():
    txns = d.transactions()
    assert sum(t["kind"] == "purchase" for t in txns) == 20
    assert sum(t["kind"] == "transfer_in" for t in txns) == 2
    assert any(t["amountCents"] == 7000 and t["memo"] == "furniture" for t in txns)
    assert all("FICA refund" not in t["memo"] for t in txns)
    assert all(isinstance(t["amountCents"], int) for t in txns)


def test_inr_conversion_is_integer_math():
    assert d.inr_to_usd_cents(50000, 8210) == 60901  # 50,000 / 82.10 = 609.0134
