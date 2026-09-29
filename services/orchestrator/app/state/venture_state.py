"""VentureState Initializer and Adapter Helpers."""

from typing import Optional
from shared.contracts.idea import FounderInput
from shared.contracts.venture_state import VentureState
from shared.enums.workflow_status import WorkflowStage


def create_initial_venture_state(
    venture_id: str,
    raw_idea: Optional[str] = None,
    founder_input: Optional[FounderInput] = None,
    user_id: Optional[str] = None,
) -> VentureState:
    """Creates a new initial VentureState with contract defaults for workflow startup."""
    if founder_input is None:
        idea_text = raw_idea or "AI venture concept"
        founder_input = FounderInput(
            startup_idea=idea_text,
            target_market="Technology",
            target_geography="Global",
            budget=50000.0,
            timeline_months=6,
            goals="Achieve Product-Market Fit",
        )

    return VentureState(
        venture_id=venture_id,
        founder_input=founder_input,
        current_stage=WorkflowStage.INITIALIZED,
        replan_count=0,
        critique_history=[],
        warnings=[],
        human_review_required=False,
    )


__all__ = ["VentureState", "create_initial_venture_state"]
