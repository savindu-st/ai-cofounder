import pytest
from pydantic import ValidationError

from shared.contracts.revenue import FinancialParameters, UnitEconomics

try:
    from services.finance.app.validation.boundary_checks import (
        sanitize_financial_parameters,
        validate_parameter_bounds,
    )
    from services.finance.app.validation.financial_validator import FinancialValidator
    from services.finance.app.validation.invariants import (
        collect_invariant_violations,
        verify_tam_sam_som,
    )
except ImportError:
    from app.validation.boundary_checks import sanitize_financial_parameters, validate_parameter_bounds
    from app.validation.financial_validator import FinancialValidator
    from app.validation.invariants import collect_invariant_violations, verify_tam_sam_som


def _params(**overrides):
    data = dict(
        monthly_price=100.0,
        starting_customers=10,
        monthly_growth_rate=0.1,
        monthly_churn_rate=0.03,
        cogs_per_unit=20.0,
        fixed_monthly_costs=1000.0,
    )
    data.update(overrides)
    return FinancialParameters(**data)


def test_tam_sam_som():
    assert verify_tam_sam_som(1000000, 500000, 50000) is True
    assert verify_tam_sam_som(50000, 100000, 500000) is False
    assert verify_tam_sam_som(0, 0, 0) is False
    assert verify_tam_sam_som(None, 100, 50) is False
    assert verify_tam_sam_som(1000, 500, 0) is False


def test_financial_parameters_reject_negative_or_out_of_bounds_values():
    with pytest.raises(ValidationError):
        _params(monthly_price=-1)
    with pytest.raises(ValidationError):
        _params(monthly_churn_rate=1.5)
    with pytest.raises(ValidationError):
        _params(monthly_growth_rate=-0.1)


def test_validate_parameter_bounds_flags_invalid_values():
    valid = _params()
    assert validate_parameter_bounds(valid) == []

    invalid = FinancialParameters.model_construct(
        monthly_price=-1.0,
        starting_customers=-1,
        monthly_growth_rate=1.5,
        monthly_churn_rate=-0.1,
        cogs_per_unit=-1.0,
        fixed_monthly_costs=-10.0,
    )
    violations = validate_parameter_bounds(invalid)
    assert len(violations) >= 5


def test_sanitize_financial_parameters_clamps_raw_values():
    sanitized = sanitize_financial_parameters(
        {
            "monthly_price": -10,
            "starting_customers": -3,
            "monthly_growth_rate": 2.0,
            "monthly_churn_rate": -1.0,
            "cogs_per_unit": 9999,
            "fixed_monthly_costs": -50,
        }
    )
    assert sanitized["monthly_price"] == 0.0
    assert sanitized["starting_customers"] == 0
    assert sanitized["monthly_growth_rate"] == 1.0
    assert sanitized["monthly_churn_rate"] == 0.0
    assert sanitized["cogs_per_unit"] == 0.0
    assert sanitized["fixed_monthly_costs"] == 0.0


def test_invariant_collection_flags_market_and_unit_economics():
    params = _params(monthly_churn_rate=0.5, cogs_per_unit=95)
    unit = UnitEconomics(
        arpu=100,
        gross_margin=0.05,
        cac=500,
        ltv=10,
        ltv_cac_ratio=0.02,
        cac_payback_months=100,
    )
    violations = collect_invariant_violations(params, unit, tam=100, sam=200, som=300)
    joined = " ".join(violations)
    assert "Market sizing invariant" in joined
    assert "LTV:CAC" in joined


def test_financial_validator_accepts_viable_parameters():
    params = _params()
    unit = UnitEconomics(
        arpu=100,
        gross_margin=0.8,
        cac=100,
        ltv=2666.67,
        ltv_cac_ratio=26.67,
        cac_payback_months=1.25,
    )
    validator = FinancialValidator()
    assert validator.validate(params, unit, tam=1_000_000, sam=500_000, som=50_000) == []
