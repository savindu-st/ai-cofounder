from shared.contracts.critic import CriticValidationOutput
from shared.contracts.idea import FounderInput
from shared.contracts.revenue import (
    FinancialParameters,
    ProjectionScenario,
    RevenueEstimationOutput,
)
from shared.contracts.venture_state import VentureState
from shared.enums.confidence_level import ValidationStatus
from shared.enums.workflow_status import WorkflowStage

from services.orchestrator.app.graph.routing import (
    route_after_critic,
    route_after_human_review,
    route_after_replanning,
    route_after_revenue,
)
from services.orchestrator.app.orchestration.human_review import (
    HumanReviewAction,
    apply_human_review,
)
from services.orchestrator.app.orchestration.replanning import (
    REPLAN_FINANCE,
    REPLAN_IDEA,
    REPLAN_MARKET,
    build_critique_context,
    build_replan_updates,
    consecutive_oscillations,
    determine_replan_target,
    needs_financial_replan,
)


def _state(**overrides):
    data = {
        "venture_id": "replan-test",
        "founder_input": FounderInput(
            startup_idea="AI code review assistant for engineering teams",
            target_market="Developer Tools",
        ),
    }
    data.update(overrides)
    return VentureState(**data)


def _critic(status, claims=None, pivot=False):
    return CriticValidationOutput(
        status=status,
        confidence_score=0.4,
        unsupported_claims=claims or [],
        verified_sources_count=0,
        feedback_notes="feedback",
        requires_pivot=pivot,
    )


def _revenue(valid=True, violations=None):
    params = FinancialParameters(
        monthly_price=100,
        starting_customers=10,
        monthly_growth_rate=0.1,
        monthly_churn_rate=0.03,
    )
    scenario = ProjectionScenario(
        scenario_name="moderate",
        month_12_revenue=1000,
        month_12_customers=10,
    )
    return RevenueEstimationOutput(
        pricing_strategy="subscription",
        parameters=params,
        scenarios=[scenario],
        tam_sam_som_valid=valid,
        invariant_violations=violations or [],
    )


def test_determine_target_market_for_research_required():
    state = _state(market_validation=_critic(ValidationStatus.RESEARCH_REQUIRED, ["missing source"]))
    assert determine_replan_target(state) == REPLAN_MARKET


def test_determine_target_idea_for_pivot():
    state = _state(
        market_validation=_critic(
            ValidationStatus.REANALYSIS_REQUIRED, ["no demand"], pivot=True
        )
    )
    assert determine_replan_target(state) == REPLAN_IDEA


def test_determine_finance_target_until_retune_budget_exhausted():
    state = _state(
        market_validation=_critic(ValidationStatus.VALID),
        revenue_estimation=_revenue(valid=False, violations=["Market sizing invariant failed."]),
    )
    assert needs_financial_replan(state)
    assert determine_replan_target(state) == REPLAN_FINANCE

    state.finance_retune_count = 2
    assert determine_replan_target(state) == REPLAN_MARKET


def test_build_replan_updates_increments_target_counters():
    state = _state(
        market_validation=_critic(ValidationStatus.RESEARCH_REQUIRED, ["missing source"]),
        critique_history=[_critic(ValidationStatus.RESEARCH_REQUIRED, ["missing source"])],
    )
    decision = build_replan_updates(state)
    assert decision.target == REPLAN_MARKET
    assert decision.updates["current_stage"] == WorkflowStage.REPLANNING
    assert decision.updates["replan_count"] == 1
    assert decision.updates["market_replan_count"] == 1
    assert decision.updates["replan_target"] == REPLAN_MARKET
    assert any("market_research required" in warning for warning in decision.updates["warnings"])


def test_oscillation_detection_and_context():
    item = _critic(ValidationStatus.RESEARCH_REQUIRED, ["same issue"])
    history = [item, item, item]
    assert consecutive_oscillations(history) == 3
    state = _state(critique_history=history, market_validation=item)
    decision = build_replan_updates(state)
    assert decision.is_oscillating
    assert any("Anti-oscillation" in warning for warning in decision.updates["warnings"])

    context = build_critique_context(history)
    assert "RESEARCH_REQUIRED" in context
    assert "same issue" in context
    assert "Validation attempts so far: 3" in context


def test_routing_uses_replanning_and_actions():
    valid = _state(market_validation=_critic(ValidationStatus.VALID))
    invalid = _state(market_validation=_critic(ValidationStatus.RESEARCH_REQUIRED, ["x"]))
    assert route_after_critic(valid) == "business_model"
    assert route_after_critic(invalid) == "replanning"

    assert route_after_revenue(_state(revenue_estimation=_revenue(valid=True))) == "marketing_plan"
    assert route_after_revenue(_state(revenue_estimation=_revenue(valid=False))) == "replanning"

    target = _state(replan_target=REPLAN_IDEA)
    assert route_after_replanning(target) == "idea_analysis"
    assert route_after_replanning(_state(replan_target=REPLAN_MARKET)) == "market_research"
    assert route_after_replanning(_state(replan_target=REPLAN_FINANCE)) == "revenue_estimation"

    assert route_after_human_review(_state(human_review_action="PROCEED_ANYWAY")) == "business_model"
    assert route_after_human_review(_state(human_review_action="OVERRIDE_ASSUMPTIONS")) == "idea_analysis"
    assert route_after_human_review(_state(human_review_action="ABORT")) == "end"


def test_human_review_actions_update_real_state_fields():
    state = _state(human_review_required=True)
    proceed = apply_human_review(state, HumanReviewAction.PROCEED_ANYWAY, "looks good")
    assert proceed["human_review_required"] is False
    assert proceed["human_review_action"] == "PROCEED_ANYWAY"
    assert proceed["human_review_notes"] == "looks good"
    assert proceed["replan_target"] == "business_model"

    override = apply_human_review(state, "OVERRIDE_ASSUMPTIONS", "change pricing")
    assert override["replan_target"] == "idea_analysis"

    abort = apply_human_review(state, "ABORT", "stop")
    assert abort["current_stage"] == WorkflowStage.FAILED
    assert abort["replan_target"] is None
    assert any("aborted" in warning.lower() for warning in abort["warnings"])
