"""Schemas for LLM-driven financial parameter extraction."""

from typing import Any, Dict, List

from pydantic import Field

from shared.contracts.base import BaseContract
from shared.contracts.revenue import FinancialParameters


class ExtractedFinancialParameters(BaseContract):
    """Strict parameter extraction result before deterministic math execution."""

    monthly_price: float = Field(gt=0)
    starting_customers: int = Field(ge=1)
    monthly_growth_rate: float = Field(ge=0.0, le=1.0)
    monthly_churn_rate: float = Field(ge=0.0, le=1.0)
    cogs_per_unit: float = Field(ge=0)
    fixed_monthly_costs: float = Field(ge=0)
    cac: float = Field(ge=0)
    starting_capital: float = Field(ge=0)
    assumptions: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)

    def to_financial_parameters(self) -> FinancialParameters:
        return FinancialParameters(
            monthly_price=self.monthly_price,
            starting_customers=self.starting_customers,
            monthly_growth_rate=self.monthly_growth_rate,
            monthly_churn_rate=self.monthly_churn_rate,
            cogs_per_unit=self.cogs_per_unit,
            fixed_monthly_costs=self.fixed_monthly_costs,
        )

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> "ExtractedFinancialParameters":
        """Sanitizes loose LLM/fallback output before strict validation."""
        from services.finance.app.validation.boundary_checks import sanitize_financial_parameters

        sanitized = sanitize_financial_parameters(raw)
        if sanitized["monthly_price"] <= 0 or sanitized["starting_customers"] < 1:
            raise ValueError("Extraction must include a positive price and at least one customer.")

        return cls(
            monthly_price=max(0.01, sanitized["monthly_price"]),
            starting_customers=max(1, sanitized["starting_customers"]),
            monthly_growth_rate=sanitized["monthly_growth_rate"],
            monthly_churn_rate=sanitized["monthly_churn_rate"],
            cogs_per_unit=sanitized["cogs_per_unit"],
            fixed_monthly_costs=sanitized["fixed_monthly_costs"],
            cac=max(0.0, float(raw.get("cac", 0.0) or 0.0)),
            starting_capital=max(0.0, float(raw.get("starting_capital", 0.0) or 0.0)),
            assumptions=list(raw.get("assumptions", []) or []),
            confidence=min(1.0, max(0.0, float(raw.get("confidence", 0.7) or 0.7))),
        )
