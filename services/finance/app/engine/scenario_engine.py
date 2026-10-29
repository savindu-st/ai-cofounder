"""Three-scenario deterministic simulation engine."""

from typing import Dict, List

from shared.contracts.revenue import FinancialParameters, ProjectionScenario

try:
    from services.finance.app.engine.calculator import (
        calculate_projections,
        compute_break_even_month,
    )
except ImportError:  # pragma: no cover
    from app.engine.calculator import calculate_projections, compute_break_even_month

SCENARIO_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    "conservative": {"growth": 0.7, "churn": 1.3, "cac": 1.25},
    "moderate": {"growth": 1.0, "churn": 1.0, "cac": 1.0},
    "optimistic": {"growth": 1.4, "churn": 0.8, "cac": 0.85},
}


def apply_scenario(
    parameters: FinancialParameters,
    scenario_name: str,
) -> FinancialParameters:
    """Returns a copy of parameters adjusted by the scenario multipliers."""
    factors = SCENARIO_MULTIPLIERS.get(scenario_name, SCENARIO_MULTIPLIERS["moderate"])
    growth = min(1.0, max(0.0, parameters.monthly_growth_rate * factors["growth"]))
    churn = min(0.99, max(0.0, parameters.monthly_churn_rate * factors["churn"]))
    return parameters.model_copy(
        update={
            "monthly_growth_rate": growth,
            "monthly_churn_rate": churn,
        }
    )


def build_scenario(
    parameters: FinancialParameters,
    scenario_name: str,
    months: int = 12,
    cac: float = 0.0,
    starting_capital: float = 0.0,
) -> ProjectionScenario:
    """Builds a single typed scenario with full monthly projections."""
    adjusted = apply_scenario(parameters, scenario_name)
    factors = SCENARIO_MULTIPLIERS.get(scenario_name, SCENARIO_MULTIPLIERS["moderate"])
    scenario_cac = max(0.0, cac * factors["cac"])

    rows = calculate_projections(
        starting_customers=adjusted.starting_customers,
        monthly_price=adjusted.monthly_price,
        growth_rate=adjusted.monthly_growth_rate,
        churn_rate=adjusted.monthly_churn_rate,
        months=months,
        cogs_per_unit=adjusted.cogs_per_unit,
        fixed_monthly_costs=adjusted.fixed_monthly_costs,
        cac=scenario_cac,
        starting_capital=starting_capital,
    )

    month_12 = rows[11] if len(rows) >= 12 else (rows[-1] if rows else None)

    return ProjectionScenario(
        scenario_name=scenario_name,
        month_12_revenue=float(month_12["revenue"]) if month_12 else 0.0,
        month_12_customers=int(month_12["customers"]) if month_12 else 0,
        break_even_month=compute_break_even_month(rows),
        month_12_mrr=float(month_12["mrr"]) if month_12 else 0.0,
        month_12_arr=float(month_12["arr"]) if month_12 else 0.0,
        ending_cash_reserve=float(rows[-1]["cash_reserve"]) if rows else 0.0,
        ending_runway_months=float(rows[-1]["runway_months"]) if rows else 0.0,
        monthly_projections=rows,
    )


def build_scenarios(
    parameters: FinancialParameters,
    months: int = 12,
    cac: float = 0.0,
    starting_capital: float = 0.0,
) -> List[ProjectionScenario]:
    """Builds Conservative, Moderate, and Optimistic scenarios in order."""
    return [
        build_scenario(parameters, name, months, cac, starting_capital)
        for name in ("conservative", "moderate", "optimistic")
    ]
