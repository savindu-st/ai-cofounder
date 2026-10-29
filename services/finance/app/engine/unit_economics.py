"""Unit economics calculations for the deterministic finance engine."""

from typing import Any

try:
    from services.finance.app.engine.calculator import _as_non_negative, _clamp_probability
except ImportError:  # pragma: no cover
    from app.engine.calculator import _as_non_negative, _clamp_probability

from shared.contracts.revenue import FinancialParameters, UnitEconomics


def calculate_unit_economics(
    parameters: FinancialParameters,
    cac: float = 0.0,
) -> UnitEconomics:
    """Calculates ARPU, gross margin, LTV, LTV:CAC, and CAC payback.

    LTV uses the standard subscription formula:
        LTV = ARPU * gross_margin / monthly_churn

    If churn is zero, LTV is capped at a 120-month lifetime to avoid infinity.
    """
    price = _as_non_negative(parameters.monthly_price)
    cogs = _as_non_negative(parameters.cogs_per_unit)
    churn = _clamp_probability(parameters.monthly_churn_rate)
    acquisition_cost = _as_non_negative(cac)

    if price > 0:
        gross_margin = min(1.0, max(0.0, (price - cogs) / price))
    else:
        gross_margin = 0.0

    if churn > 0:
        ltv = (price * gross_margin) / churn
    else:
        ltv = price * gross_margin * 120.0

    if acquisition_cost > 0:
        ltv_cac_ratio = ltv / acquisition_cost
    else:
        ltv_cac_ratio = 0.0

    monthly_gross_profit = price * gross_margin
    if monthly_gross_profit > 0:
        cac_payback_months = acquisition_cost / monthly_gross_profit
    else:
        cac_payback_months = 0.0

    return UnitEconomics(
        arpu=round(price, 2),
        gross_margin=round(gross_margin, 4),
        cac=round(acquisition_cost, 2),
        ltv=round(ltv, 2),
        ltv_cac_ratio=round(ltv_cac_ratio, 2),
        cac_payback_months=round(cac_payback_months, 2),
    )
