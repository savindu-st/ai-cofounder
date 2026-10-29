"""Mathematical boundary checks and parameter sanitization."""

from typing import Any, Dict, List

from shared.contracts.revenue import FinancialParameters


def clamp_probability(value: Any) -> float:
    try:
        return min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def ensure_non_negative(value: Any) -> float:
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.0


def validate_parameter_bounds(parameters: FinancialParameters) -> List[str]:
    """Returns violations for impossible or invalid financial parameters."""
    violations: List[str] = []

    if parameters.monthly_price < 0:
        violations.append("Monthly price cannot be negative.")
    if parameters.starting_customers < 0:
        violations.append("Starting customers cannot be negative.")
    if not (0.0 <= parameters.monthly_growth_rate <= 1.0):
        violations.append("Monthly growth rate must be between 0.0 and 1.0.")
    if not (0.0 <= parameters.monthly_churn_rate <= 1.0):
        violations.append("Monthly churn rate must be between 0.0 and 1.0.")
    if parameters.cogs_per_unit < 0:
        violations.append("COGS per unit cannot be negative.")
    if parameters.fixed_monthly_costs < 0:
        violations.append("Fixed monthly costs cannot be negative.")

    return violations


def sanitize_financial_parameters(data: Dict[str, Any]) -> Dict[str, Any]:
    """Clamps raw extraction output into safe, contract-compatible bounds."""
    price = ensure_non_negative(data.get("monthly_price", 0.0))
    cogs = ensure_non_negative(data.get("cogs_per_unit", 0.0))
    if price > 0:
        cogs = min(cogs, price * 0.95)
    else:
        cogs = 0.0

    return {
        "monthly_price": round(price, 2),
        "starting_customers": max(0, int(ensure_non_negative(data.get("starting_customers", 0)))),
        "monthly_growth_rate": clamp_probability(data.get("monthly_growth_rate", 0.0)),
        "monthly_churn_rate": clamp_probability(data.get("monthly_churn_rate", 0.0)),
        "cogs_per_unit": round(cogs, 2),
        "fixed_monthly_costs": round(ensure_non_negative(data.get("fixed_monthly_costs", 0.0)), 2),
    }
