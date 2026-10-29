"""Sensitivity analysis matrix for price and churn shocks."""

from typing import List

from shared.contracts.revenue import (
    FinancialParameters,
    SensitivityCell,
    SensitivityMatrix,
)

try:
    from services.finance.app.engine.calculator import calculate_projections
    from services.finance.app.engine.unit_economics import calculate_unit_economics
except ImportError:  # pragma: no cover
    from app.engine.calculator import calculate_projections
    from app.engine.unit_economics import calculate_unit_economics

PRICE_SHOCKS = (-0.2, 0.0, 0.2)
CHURN_SHOCKS = (-0.2, 0.0, 0.2)


def build_sensitivity_matrix(
    parameters: FinancialParameters,
    cac: float = 0.0,
    months: int = 12,
    starting_capital: float = 0.0,
) -> SensitivityMatrix:
    """Computes month-12 revenue and LTV under ±20% price/churn shocks."""
    cells: List[SensitivityCell] = []

    baseline_rows = calculate_projections(
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
    baseline_month_12 = baseline_rows[11] if len(baseline_rows) >= 12 else (baseline_rows[-1] if baseline_rows else {})
    baseline_econ = calculate_unit_economics(parameters, cac=cac)

    for price_shock in PRICE_SHOCKS:
        shocked_price = max(0.01, parameters.monthly_price * (1.0 + price_shock))
        for churn_shock in CHURN_SHOCKS:
            shocked_churn = min(0.99, max(0.0, parameters.monthly_churn_rate * (1.0 + churn_shock)))
            shocked_params = parameters.model_copy(
                update={
                    "monthly_price": shocked_price,
                    "monthly_churn_rate": shocked_churn,
                }
            )
            rows = calculate_projections(
                starting_customers=shocked_params.starting_customers,
                monthly_price=shocked_params.monthly_price,
                growth_rate=shocked_params.monthly_growth_rate,
                churn_rate=shocked_params.monthly_churn_rate,
                months=months,
                cogs_per_unit=shocked_params.cogs_per_unit,
                fixed_monthly_costs=shocked_params.fixed_monthly_costs,
                cac=cac,
                starting_capital=starting_capital,
            )
            month_12 = rows[11] if len(rows) >= 12 else (rows[-1] if rows else {})
            econ = calculate_unit_economics(shocked_params, cac=cac)
            cells.append(
                SensitivityCell(
                    price_change_pct=price_shock,
                    churn_change_pct=churn_shock,
                    month_12_revenue=float(month_12.get("revenue", 0.0)),
                    ltv=econ.ltv,
                    ltv_cac_ratio=econ.ltv_cac_ratio,
                )
            )

    return SensitivityMatrix(
        baseline_month_12_revenue=float(baseline_month_12.get("revenue", 0.0)),
        baseline_ltv=baseline_econ.ltv,
        cells=cells,
    )
