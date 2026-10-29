import pytest

from shared.contracts.revenue import FinancialParameters

try:
    from services.finance.app.engine.projections import (
        build_projections,
        generate_horizon_projections,
        summarize_projection,
    )
    from services.finance.app.engine.scenario_engine import (
        apply_scenario,
        build_scenario,
        build_scenarios,
    )
    from services.finance.app.engine.sensitivity import build_sensitivity_matrix
    from services.finance.app.engine.unit_economics import calculate_unit_economics
except ImportError:
    from app.engine.projections import build_projections, generate_horizon_projections, summarize_projection
    from app.engine.scenario_engine import apply_scenario, build_scenario, build_scenarios
    from app.engine.sensitivity import build_sensitivity_matrix
    from app.engine.unit_economics import calculate_unit_economics


@pytest.fixture
def parameters():
    return FinancialParameters(
        monthly_price=100.0,
        starting_customers=100,
        monthly_growth_rate=0.12,
        monthly_churn_rate=0.03,
        cogs_per_unit=20.0,
        fixed_monthly_costs=5000.0,
    )


def test_horizon_generation(parameters):
    tables = generate_horizon_projections(
        parameters, horizons=(12, 24, 36), cac=100, starting_capital=100000
    )
    assert set(tables) == {12, 24, 36}
    assert len(tables[12]) == 12
    assert len(tables[24]) == 24
    assert len(tables[36]) == 36


def test_summarize_projection(parameters):
    rows = build_projections(parameters, months=12, cac=100, starting_capital=100000)
    summary = summarize_projection(rows)
    assert summary["month_12_revenue"] == rows[-1]["revenue"]
    assert summary["month_12_customers"] == rows[-1]["customers"]
    assert "break_even_month" in summary


def test_scenario_multipliers(parameters):
    conservative = apply_scenario(parameters, "conservative")
    moderate = apply_scenario(parameters, "moderate")
    optimistic = apply_scenario(parameters, "optimistic")

    assert conservative.monthly_growth_rate < moderate.monthly_growth_rate < optimistic.monthly_growth_rate
    assert conservative.monthly_churn_rate > moderate.monthly_churn_rate > optimistic.monthly_churn_rate


def test_scenarios_are_monotonic(parameters):
    scenarios = build_scenarios(parameters, months=12, cac=100, starting_capital=50000)
    assert [s.scenario_name for s in scenarios] == ["conservative", "moderate", "optimistic"]
    assert scenarios[0].month_12_revenue < scenarios[1].month_12_revenue < scenarios[2].month_12_revenue
    assert all(len(s.monthly_projections) == 12 for s in scenarios)


def test_scenario_break_even_and_runway(parameters):
    scenario = build_scenario(parameters, "moderate", months=12, cac=100, starting_capital=50000)
    assert scenario.month_12_mrr == scenario.month_12_revenue
    assert scenario.month_12_arr == pytest.approx(scenario.month_12_revenue * 12, rel=1e-5)
    assert scenario.ending_cash_reserve is not None
    assert scenario.ending_runway_months is not None


def test_unit_economics(parameters):
    unit = calculate_unit_economics(parameters, cac=100)
    assert unit.arpu == 100.0
    assert unit.gross_margin == 0.8
    assert unit.ltv == pytest.approx(2666.67, rel=1e-3)
    assert unit.ltv_cac_ratio == pytest.approx(26.67, rel=1e-3)
    assert unit.cac_payback_months == pytest.approx(1.25, rel=1e-3)


def test_unit_economics_zero_churn_is_finite(parameters):
    zero_churn = parameters.model_copy(update={"monthly_churn_rate": 0.0})
    unit = calculate_unit_economics(zero_churn, cac=100)
    assert unit.ltv == pytest.approx(100 * 0.8 * 120, rel=1e-6)
    assert unit.ltv < float("inf")


def test_sensitivity_matrix_shape(parameters):
    matrix = build_sensitivity_matrix(parameters, cac=100, months=12, starting_capital=50000)
    assert len(matrix.cells) == 9
    assert matrix.baseline_month_12_revenue > 0
    assert matrix.baseline_ltv > 0
    assert {cell.price_change_pct for cell in matrix.cells} == {-0.2, 0.0, 0.2}
