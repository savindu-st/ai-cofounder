"""Conditional Routing Logic for LangGraph State Machine.

Evaluates critique rubrics, financial invariants, and persisted founder review
actions to determine branching edges in the venture workflow.
"""

from shared.contracts.venture_state import VentureState
from shared.enums.confidence_level import ValidationStatus
from services.orchestrator.app.orchestration.human_review import route_target_for_action
from services.orchestrator.app.orchestration.replanning import (
    REPLAN_HUMAN,
    REPLAN_IDEA,
    REPLAN_MARKET,
    REPLAN_FINANCE,
    needs_financial_replan,
    should_pause_for_human,
)


def route_after_critic(state: VentureState) -> str:
    """Route valid research forward, invalid research into targeted replanning."""
    if state.market_validation is None:
        return "market_research"

    if state.market_validation.status == ValidationStatus.VALID:
        return "business_model"

    if should_pause_for_human(state):
        return "human_review"

    return "replanning"


def route_after_revenue(state: VentureState) -> str:
    """Route financially sound ventures forward; otherwise enter repair loop."""
    if state.revenue_estimation is None:
        return "revenue_estimation"

    if not needs_financial_replan(state):
        return "marketing_plan"

    if should_pause_for_human(state):
        return "human_review"

    return "replanning"


def route_after_replanning(state: VentureState) -> str:
    """Dispatch a replan decision to its repair stage or to HITL."""
    target = state.replan_target
    if target == REPLAN_IDEA:
        return "idea_analysis"
    if target == REPLAN_MARKET:
        return "market_research"
    if target == REPLAN_FINANCE:
        return "revenue_estimation"
    if target == REPLAN_HUMAN:
        return "human_review"
    return "market_research"


def route_after_human_review(state: VentureState) -> str:
    """Determines continuation path from the persisted founder review action."""
    action = state.human_review_action
    if not action and state.human_review_notes in {
        "PROCEED_ANYWAY",
        "OVERRIDE_ASSUMPTIONS",
        "ABORT",
    }:
        action = state.human_review_notes
    return route_target_for_action(action)
