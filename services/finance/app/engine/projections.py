"""12-to-36 Month Projection Generators.

Wraps the core calculator with reusable horizon generation and summary helpers.
"""

from typing import Any, Dict, List, Optional, Sequence

try:
    from services.finance.app.engine.calculator import (
        calculate_projections,
        compute_break_even_month,
    )
except ImportError:  # pragma: no cover - isolated package install fallback
    from app.engine.calculator import calculate_projections, compute_break_even_month

from shared.contracts.revenue import FinancialParameters


def build_projections(
    parameters: FinancialParameters,
    months: int = 12,
    cac: float = 0.0,
    starting_capital: float = 0.0,
) -> List[Dict[str, Any]]:
    """Generates deterministic monthly rows for a single horizon."""
    return calculate_projections(
        starting_customers=parameters.starting_customers,
        monthly_price=parameters.monthly_price,
        growth_rate=parameters.monthly_growth_rate,
        churn_rate=parameters.monthly_churn_rate,
        months=months,
        cogs_per_unit=parameters.cogs_per_unit,
        fixed_monthly_costs=parameters.fixed_monthly_costs,
        cac=cac,
        starting_capital=starting_capital,
    )


def generate_horizon_projections(
    parameters: FinancialParameters,
    horizons: Sequence[int] = (12, 24, 36),
    cac: float = 0.0,
    starting_capital: float = 0.0,
) -> Dict[int, List[Dict[str, Any]]]:
    """Generates separate projection tables for every requested horizon."""
    return {
        int(horizon): build_projections(
            parameters=parameters,
            months=int(horizon),
            cac=cac,
            starting_capital=starting_capital,
        )
        for horizon in horizons
        if int(horizon) > 0
    }


def summarize_projection(rows: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    """Extracts commonly reported summary metrics from a projection table."""
    if not rows:
        return {
            "month_12_revenue": 0.0,
            "month_12_customers": 0,
            "break_even_month": None,
        }

    month_12 = rows[11] if len(rows) >= 12 else rows[-1]
    return {
        "month_12_revenue": float(month_12.get("revenue", 0.0)),
        "month_12_customers": int(month_12.get("customers", 0)),
        "break_even_month": compute_break_even_month(rows),
    }
