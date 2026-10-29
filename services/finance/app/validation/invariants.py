"""Deterministic financial invariant checkers."""

from typing import List, Optional

from shared.contracts.revenue import FinancialParameters, UnitEconomics


def verify_tam_sam_som(tam: Optional[float], sam: Optional[float], som: Optional[float]) -> bool:
    """Enforces 0 < SOM <= SAM <= TAM with safe handling of None/invalid values."""
    try:
        clean_tam = float(tam)  # type: ignore[arg-type]
        clean_sam = float(sam)  # type: ignore[arg-type]
        clean_som = float(som)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False

    return clean_tam > 0 and clean_sam > 0 and clean_som > 0 and clean_som <= clean_sam <= clean_tam


def verify_churn_bounds(parameters: FinancialParameters) -> bool:
    return 0.0 <= parameters.monthly_churn_rate <= 1.0


def verify_growth_bounds(parameters: FinancialParameters) -> bool:
    return 0.0 <= parameters.monthly_growth_rate <= 1.0


def verify_gross_margin(unit_economics: UnitEconomics) -> bool:
    return unit_economics.gross_margin > 0.0


def verify_ltv_cac(unit_economics: UnitEconomics, minimum_ratio: float = 3.0) -> bool:
    return unit_economics.ltv_cac_ratio >= minimum_ratio


def collect_invariant_violations(
    parameters: FinancialParameters,
    unit_economics: UnitEconomics,
    tam: Optional[float] = None,
    sam: Optional[float] = None,
    som: Optional[float] = None,
    minimum_ltv_cac: float = 3.0,
) -> List[str]:
    """Collects human-readable invariant violations for downstream retuning."""
    violations: List[str] = []

    if not verify_tam_sam_som(tam, sam, som):
        violations.append(
            f"Market sizing invariant violated: SOM (${som or 0:,.2f}) must be > 0 and <= SAM "
            f"(${sam or 0:,.2f}) <= TAM (${tam or 0:,.2f})."
        )
    if not verify_churn_bounds(parameters):
        violations.append("Monthly churn rate must be between 0.0 and 1.0.")
    if not verify_growth_bounds(parameters):
        violations.append("Monthly growth rate must be between 0.0 and 1.0.")
    if not verify_gross_margin(unit_economics):
        violations.append("Gross margin must be greater than 0.")
    if not verify_ltv_cac(unit_economics, minimum_ltv_cac):
        violations.append(
            f"LTV:CAC ratio ({unit_economics.ltv_cac_ratio:.2f}) is below the "
            f"{minimum_ltv_cac:.1f}x venture viability threshold."
        )

    return violations
