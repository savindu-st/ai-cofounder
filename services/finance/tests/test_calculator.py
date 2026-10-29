import pytest

try:
    from services.finance.app.engine.calculator import (
        calculate_projections,
        compute_break_even_month,
    )
except ImportError:
    from app.engine.calculator import calculate_projections, compute_break_even_month


def test_calculate_projections():
    res = calculate_projections(100, 1500, 0.05, 0.02, 12)
    assert len(res) == 12
    assert res[0]["revenue"] == 150000.0
    assert res[0]["customers"] == 100
    assert res[1]["customers"] == 103


def test_projection_rows_include_full_unit_economics_trail():
    rows = calculate_projections(
        starting_customers=100,
        monthly_price=100.0,
        growth_rate=0.1,
        churn_rate=0.05,
        months=6,
        cogs_per_unit=20.0,
        fixed_monthly_costs=2000.0,
        cac=50.0,
        starting_capital=10000.0,
    )
    first = rows[0]
    for key in (
        "revenue",
        "mrr",
        "arr",
        "cogs",
        "gross_profit",
        "net_burn",
        "cash_reserve",
        "runway_months",
    ):
        assert key in first
    assert first["gross_profit"] == 8000.0
    assert first["arr"] == 120000.0


def test_projection_handles_zero_and_negative_inputs_safely():
    rows = calculate_projections(0, 0, 0, 0, 3, starting_capital=-100)
    assert len(rows) == 3
    assert rows[0]["revenue"] == 0.0
    assert rows[0]["cash_reserve"] >= 0.0
    assert rows[0]["runway_months"] == 999.0


def test_projection_empty_horizon():
    assert calculate_projections(10, 10, 0.1, 0.1, 0) == []


def test_break_even_detection():
    rows = calculate_projections(
        starting_customers=50,
        monthly_price=500.0,
        growth_rate=0.1,
        churn_rate=0.01,
        months=6,
        fixed_monthly_costs=1000.0,
    )
    assert compute_break_even_month(rows) == 1

    loss_rows = calculate_projections(
        starting_customers=1,
        monthly_price=10.0,
        growth_rate=0.0,
        churn_rate=0.0,
        months=3,
        fixed_monthly_costs=5000.0,
    )
    assert compute_break_even_month(loss_rows) is None


@pytest.mark.parametrize("months", [12, 24, 36])
def test_projection_horizons(months):
    rows = calculate_projections(10, 99, 0.1, 0.03, months)
    assert len(rows) == months
    assert rows[-1]["month"] == months
