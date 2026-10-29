"""Finance Domain Strict Interface.

Exposes the public entrypoint for Revenue Estimation and deterministic scenario
calculations. All interactions from the orchestrator or other agents must pass
through this interface.
"""

import logging
import os
from typing import Any, List, Optional

from shared.contracts.business_model import BusinessModelOutput
from shared.contracts.idea import FounderInput, IdeaAnalysisOutput
from shared.contracts.market import MarketResearchOutput
from shared.contracts.revenue import RevenueEstimationOutput

try:
    from services.finance.app.agents.revenue_estimation.agent import RevenueParameterAgent
    from services.finance.app.engine.scenario_engine import build_scenarios
    from services.finance.app.engine.sensitivity import build_sensitivity_matrix
    from services.finance.app.engine.unit_economics import calculate_unit_economics
    from services.finance.app.validation.financial_validator import FinancialValidator
    from services.finance.app.validation.invariants import verify_tam_sam_som
except ImportError:  # pragma: no cover
    from app.agents.revenue_estimation.agent import RevenueParameterAgent
    from app.engine.scenario_engine import build_scenarios
    from app.engine.sensitivity import build_sensitivity_matrix
    from app.engine.unit_economics import calculate_unit_economics
    from app.validation.financial_validator import FinancialValidator
    from app.validation.invariants import verify_tam_sam_som

logger = logging.getLogger(__name__)

_agent: Optional[RevenueParameterAgent] = None


def _get_llm() -> Optional[Any]:
    """Instantiates an LLM only when provider credentials are configured."""
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and not openai_key.startswith("your-") and openai_key != "mock":
        try:
            from langchain_openai import ChatOpenAI

            model_name = os.getenv("FINANCE_MODEL", os.getenv("DEFAULT_MODEL", "gpt-4o-mini"))
            return ChatOpenAI(model=model_name, api_key=openai_key, temperature=0.1)
        except Exception as exc:
            logger.debug("[Finance Interface] Could not initialize ChatOpenAI: %s", exc)
    return None


def get_revenue_agent() -> RevenueParameterAgent:
    global _agent
    if _agent is None:
        _agent = RevenueParameterAgent(llm=_get_llm())
    return _agent


def run_revenue_estimation(
    idea: IdeaAnalysisOutput,
    market: MarketResearchOutput,
    business_model: BusinessModelOutput,
    horizon_months: int = 12,
    founder: Optional[FounderInput] = None,
    critique_notes: Optional[str] = None,
    retune_round: int = 0,
) -> RevenueEstimationOutput:
    """Extracts assumptions and computes deterministic multi-scenario projections.

    Tier-1 micro-retuning is applied internally (up to two rounds) when unit
    economics fall below the LTV:CAC viability threshold, while the market
    sizing invariant remains valid. Market invariant failures are surfaced in
    ``invariant_violations`` for the orchestrator's Tier-2 loopback.
    """
    agent = get_revenue_agent()
    validator = FinancialValidator()

    tam = market.tam_estimate
    sam = market.sam_estimate
    som = market.som_estimate
    market_valid = verify_tam_sam_som(tam, sam, som)

    assumptions = agent.extract(
        idea=idea,
        market=market,
        business_model=business_model,
        founder=founder,
        retune_notes=critique_notes,
        retune_round=retune_round,
    )
    parameters = assumptions.to_financial_parameters()
    unit_economics = calculate_unit_economics(parameters, cac=assumptions.cac)
    violations = validator.validate(
        parameters=parameters,
        unit_economics=unit_economics,
        tam=tam,
        sam=sam,
        som=som,
    )

    # Tier-1 internal retune: only when the market invariant is sound but unit
    # economics are unviable. Do not retune our way around a market sizing error.
    internal_retunes = 0
    while (
        market_valid
        and any("LTV:CAC" in violation for violation in violations)
        and internal_retunes < 2
    ):
        internal_retunes += 1
        assumptions = agent.extract(
            idea=idea,
            market=market,
            business_model=business_model,
            founder=founder,
            retune_notes=critique_notes,
            retune_round=retune_round + internal_retunes,
        )
        parameters = assumptions.to_financial_parameters()
        unit_economics = calculate_unit_economics(parameters, cac=assumptions.cac)
        violations = validator.validate(
            parameters=parameters,
            unit_economics=unit_economics,
            tam=tam,
            sam=sam,
            som=som,
        )

    scenarios = build_scenarios(
        parameters=parameters,
        months=horizon_months,
        cac=assumptions.cac,
        starting_capital=assumptions.starting_capital,
    )
    sensitivity = build_sensitivity_matrix(
        parameters=parameters,
        cac=assumptions.cac,
        months=horizon_months,
        starting_capital=assumptions.starting_capital,
    )

    revenue_streams = business_model.canvas.revenue_streams or []
    pricing_strategy = (
        revenue_streams[0]
        if revenue_streams
        else "Tiered subscription pricing anchored to competitor benchmarks"
    )

    summary: List[str] = list(assumptions.assumptions)
    summary.extend(
        [
            f"Base monthly price: ${parameters.monthly_price:,.2f}",
            f"Starting customers: {parameters.starting_customers}",
            f"Monthly growth assumption: {parameters.monthly_growth_rate * 100:.1f}%",
            f"Monthly churn assumption: {parameters.monthly_churn_rate * 100:.1f}%",
            f"Estimated CAC: ${assumptions.cac:,.2f}",
            f"Starting capital: ${assumptions.starting_capital:,.2f}",
            f"Unit economics: LTV ${unit_economics.ltv:,.2f}, "
            f"LTV:CAC {unit_economics.ltv_cac_ratio:.2f}x, "
            f"payback {unit_economics.cac_payback_months:.1f} months.",
        ]
    )
    if internal_retunes:
        summary.append(f"Internal finance retune rounds applied: {internal_retunes}.")
    if violations:
        summary.extend(f"Validator: {violation}" for violation in violations)

    return RevenueEstimationOutput(
        pricing_strategy=pricing_strategy,
        parameters=parameters,
        scenarios=scenarios,
        tam_sam_som_valid=market_valid,
        assumptions_summary=summary,
        unit_economics=unit_economics,
        sensitivity=sensitivity,
        invariant_violations=violations,
        horizon_months=horizon_months,
    )
