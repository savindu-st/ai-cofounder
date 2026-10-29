"""Financial validator pipeline combining market, parameter, and unit economics checks."""

from typing import List, Optional

from shared.contracts.revenue import FinancialParameters, UnitEconomics
from services.finance.app.validation.boundary_checks import validate_parameter_bounds
from services.finance.app.validation.invariants import (
    collect_invariant_violations,
    verify_tam_sam_som,
)


class FinancialValidator:
    """Single entrypoint for deterministic financial validation."""

    def __init__(self, minimum_ltv_cac: float = 3.0):
        self.minimum_ltv_cac = minimum_ltv_cac

    def validate_market(
        self,
        tam: Optional[float],
        sam: Optional[float],
        som: Optional[float],
    ) -> bool:
        return verify_tam_sam_som(tam, sam, som)

    def validate_parameters(self, parameters: FinancialParameters) -> List[str]:
        return validate_parameter_bounds(parameters)

    def validate(
        self,
        parameters: FinancialParameters,
        unit_economics: UnitEconomics,
        tam: Optional[float] = None,
        sam: Optional[float] = None,
        som: Optional[float] = None,
    ) -> List[str]:
        """Returns every invariant/parameter violation for the current projection."""
        violations = self.validate_parameters(parameters)
        violations.extend(
            collect_invariant_violations(
                parameters=parameters,
                unit_economics=unit_economics,
                tam=tam,
                sam=sam,
                som=som,
                minimum_ltv_cac=self.minimum_ltv_cac,
            )
        )
        # De-duplicate while preserving order.
        return list(dict.fromkeys(violations))


def validate_financial_parameters(parameters: FinancialParameters) -> List[str]:
    """Convenience wrapper used by unit tests and callers."""
    return FinancialValidator().validate_parameters(parameters)
