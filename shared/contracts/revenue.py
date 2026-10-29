from typing import List, Dict, Any, Optional
from pydantic import Field
from shared.contracts.base import BaseContract

class FinancialParameters(BaseContract):
    monthly_price: float = Field(ge=0)
    starting_customers: int = Field(ge=0)
    monthly_growth_rate: float = Field(ge=0.0, le=1.0)
    monthly_churn_rate: float = Field(ge=0.0, le=1.0)
    cogs_per_unit: float = Field(default=0.0, ge=0)
    fixed_monthly_costs: float = Field(default=0.0, ge=0)

class UnitEconomics(BaseContract):
    """Deterministic unit economics derived from financial parameters."""
    arpu: float = Field(default=0.0, ge=0)
    gross_margin: float = Field(default=0.0, ge=0, le=1)
    cac: float = Field(default=0.0, ge=0)
    ltv: float = Field(default=0.0, ge=0)
    ltv_cac_ratio: float = Field(default=0.0, ge=0)
    cac_payback_months: float = Field(default=0.0, ge=0)

class SensitivityCell(BaseContract):
    price_change_pct: float
    churn_change_pct: float
    month_12_revenue: float = 0.0
    ltv: float = 0.0
    ltv_cac_ratio: float = 0.0

class SensitivityMatrix(BaseContract):
    baseline_month_12_revenue: float = 0.0
    baseline_ltv: float = 0.0
    cells: List[SensitivityCell] = Field(default_factory=list)

class ProjectionScenario(BaseContract):
    scenario_name: str  # "conservative", "moderate", "optimistic"
    month_12_revenue: float
    month_12_customers: int
    break_even_month: Optional[int] = None
    month_12_mrr: Optional[float] = None
    month_12_arr: Optional[float] = None
    ending_cash_reserve: Optional[float] = None
    ending_runway_months: Optional[float] = None
    monthly_projections: List[Dict[str, Any]] = Field(default_factory=list)

class RevenueEstimationOutput(BaseContract):
    pricing_strategy: str
    parameters: FinancialParameters
    scenarios: List[ProjectionScenario]
    tam_sam_som_valid: bool = True
    assumptions_summary: List[str] = Field(default_factory=list)
    unit_economics: Optional[UnitEconomics] = None
    sensitivity: Optional[SensitivityMatrix] = None
    invariant_violations: List[str] = Field(default_factory=list)
    horizon_months: int = Field(default=12, ge=1)
