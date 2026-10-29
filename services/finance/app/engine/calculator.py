"""Deterministic Financial Calculation Engine.

All financial projections are computed with pure Python arithmetic. LLMs never
perform revenue math in this module. Every monthly row includes the full unit
economics trail required for auditing and frontend display.
"""

from typing import Any, Dict, List

MAX_RUNWAY_MONTHS = 999.0


def _as_non_negative(value: Any) -> float:
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.0


def _clamp_probability(value: Any) -> float:
    try:
        return min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def compute_break_even_month(rows: List[Dict[str, Any]]) -> int | None:
    """Returns the first month where net burn is non-positive, if any."""
    for row in rows:
        if row.get("net_burn", 0.0) <= 0:
            return int(row["month"])
    return None


def calculate_projections(
    starting_customers: int,
    monthly_price: float,
    growth_rate: float,
    churn_rate: float,
    months: int = 12,
    cogs_per_unit: float = 0.0,
    fixed_monthly_costs: float = 0.0,
    cac: float = 0.0,
    starting_capital: float = 0.0,
) -> List[Dict[str, Any]]:
    """Builds a month-by-month deterministic projection.

    Month 0 semantics match the original engine: revenue in month 1 is the
    starting customer base multiplied by the monthly price, then the customer
    base grows by acquisitions and shrinks by churn for the next month.

    Args:
        starting_customers: Active paying customers at the start of month 1.
        monthly_price: ARPU / subscription price per customer per month.
        growth_rate: Monthly customer acquisition rate applied to active users.
        churn_rate: Monthly fraction of active customers lost.
        months: Projection horizon (12, 24, or 36 months typically).
        cogs_per_unit: Variable cost to serve one active customer per month.
        fixed_monthly_costs: Fixed operating overhead per month.
        cac: Customer acquisition cost applied to new acquisitions.
        starting_capital: Cash reserve available at the start.

    Returns:
        List of monthly projection dictionaries.
    """
    horizon = int(months)
    if horizon <= 0:
        return []

    active = _as_non_negative(starting_customers)
    price = _as_non_negative(monthly_price)
    growth = _as_non_negative(growth_rate)
    churn = _clamp_probability(churn_rate)
    cogs_unit = _as_non_negative(cogs_per_unit)
    fixed = _as_non_negative(fixed_monthly_costs)
    acquisition_cost = _as_non_negative(cac)
    cash = _as_non_negative(starting_capital)

    projections: List[Dict[str, Any]] = []

    for month in range(1, horizon + 1):
        revenue = active * price
        cogs = active * cogs_unit
        gross_profit = revenue - cogs

        new_customers = active * growth
        churned_customers = active * churn
        acquisition_spend = new_customers * acquisition_cost
        net_burn = fixed + acquisition_spend - gross_profit
        cash -= net_burn

        if net_burn > 0:
            runway_months = max(0.0, cash) / max(1.0, net_burn)
        else:
            runway_months = MAX_RUNWAY_MONTHS

        projections.append(
            {
                "month": month,
                "customers": int(round(active)),
                "active_customers": round(active, 4),
                "new_customers": round(new_customers, 4),
                "churned_customers": round(churned_customers, 4),
                "revenue": round(revenue, 2),
                "mrr": round(revenue, 2),
                "arr": round(revenue * 12.0, 2),
                "cogs": round(cogs, 2),
                "gross_profit": round(gross_profit, 2),
                "acquisition_spend": round(acquisition_spend, 2),
                "net_burn": round(net_burn, 2),
                "cash_reserve": round(cash, 2),
                "runway_months": round(runway_months, 2),
                "is_break_even": net_burn <= 0,
            }
        )

        active = max(0.0, active - churned_customers + new_customers)

    return projections
