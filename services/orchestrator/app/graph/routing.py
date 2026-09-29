"""Conditional Routing Logic for LangGraph State Machine.

Evaluates critique rubrics, financial invariants, and human review actions
to determine branching edges in the venture workflow.
"""

from shared.contracts.venture_state import VentureState
from shared.enums.confidence_level import ValidationStatus
from shared.enums.workflow_status import WorkflowStage


def route_after_critic(state: VentureState) -> str:
    """Evaluates Critic validation results to decide next stage."""
    # Ceiling check: route to HITL pause if total replans exceed 5
    if state.replan_count >= 5:
        return "human_review"

    if state.market_validation is None:
        return "market_research"

    # Happy path: validation passes rubric
    if state.market_validation.status == ValidationStatus.VALID:
        return "business_model"

    # Pivot or structural flaw requires rebuilding value proposition
    if state.market_validation.requires_pivot or state.market_validation.status == ValidationStatus.REANALYSIS_REQUIRED:
        state.replan_count += 1
        return "idea_analysis"

    # Weak citations or insufficient sources triggers targeted market research
    if state.market_validation.status in (ValidationStatus.RESEARCH_REQUIRED, ValidationStatus.LOW_CONFIDENCE):
        state.replan_count += 1
        state.market_replan_count += 1
        return "market_research"

    return "business_model"


def route_after_revenue(state: VentureState) -> str:
    """Evaluates financial parameters and market scale invariants."""
    if state.revenue_estimation is None:
        return "revenue_estimation"

    # Invariants valid: SOM <= SAM <= TAM and positive gross margin
    if state.revenue_estimation.tam_sam_som_valid:
        return "marketing_plan"

    # Ceiling check
    if state.replan_count >= 5:
        return "human_review"

    # Tier 1: Internal financial parameter retuning (up to 2 retunes)
    if state.finance_retune_count < 2:
        state.finance_retune_count += 1
        return "revenue_estimation"

    # Tier 2: Boundary violation persists; send back to market research with critique notes
    state.replan_count += 1
    return "market_research"


def route_after_human_review(state: VentureState) -> str:
    """Determines continuation path after founder review action."""
    if state.current_stage == WorkflowStage.FAILED or state.human_review_notes == "ABORT":
        return "end"

    if state.human_review_notes == "OVERRIDE_ASSUMPTIONS":
        return "idea_analysis"

    # Default action: PROCEED_ANYWAY
    return "business_model"
