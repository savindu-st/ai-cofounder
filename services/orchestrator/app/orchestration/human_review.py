"""Human-in-the-Loop action handling.

Centralizes the founder decision vocabulary so the graph, coordinator, and API
all persist and interpret review actions consistently.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from shared.contracts.venture_state import VentureState
from shared.enums.workflow_status import WorkflowStage


class HumanReviewAction(str, Enum):
    PROCEED_ANYWAY = "PROCEED_ANYWAY"
    OVERRIDE_ASSUMPTIONS = "OVERRIDE_ASSUMPTIONS"
    ABORT = "ABORT"


VALID_REVIEW_ACTIONS = tuple(action.value for action in HumanReviewAction)


def normalize_review_action(
    action: Optional[str] = None,
    human_approved: Optional[bool] = None,
) -> HumanReviewAction:
    """Coerce legacy boolean approvals or raw strings into a valid action."""
    if action:
        try:
            return HumanReviewAction(action)
        except ValueError as exc:
            raise ValueError(
                f"Invalid human review action '{action}'. Expected one of {VALID_REVIEW_ACTIONS}."
            ) from exc
    if human_approved is False:
        return HumanReviewAction.ABORT
    return HumanReviewAction.PROCEED_ANYWAY


def apply_human_review(
    state: VentureState,
    action: HumanReviewAction | str,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    """Return the state delta that records and applies a founder decision."""
    normalized = normalize_review_action(
        action.value if isinstance(action, HumanReviewAction) else action
    )
    warnings = list(state.warnings)

    if notes and notes not in warnings:
        warnings.append(f"Founder review note: {notes}")

    updates: dict[str, Any] = {
        "human_review_required": False,
        "human_review_action": normalized.value,
        "human_review_notes": notes,
    }

    if normalized == HumanReviewAction.ABORT:
        updates["current_stage"] = WorkflowStage.FAILED
        updates["replan_target"] = None
        abort_note = "Venture aborted by founder during human review."
        if abort_note not in warnings:
            warnings.append(abort_note)
    elif normalized == HumanReviewAction.OVERRIDE_ASSUMPTIONS:
        updates["current_stage"] = WorkflowStage.REPLANNING
        updates["replan_target"] = "idea_analysis"
    else:
        updates["current_stage"] = WorkflowStage.REPLANNING
        updates["replan_target"] = "business_model"

    updates["warnings"] = warnings
    return updates


def route_target_for_action(action: Optional[str]) -> str:
    """Map a persisted review action to the next graph node."""
    if action == HumanReviewAction.ABORT.value:
        return "end"
    if action == HumanReviewAction.OVERRIDE_ASSUMPTIONS.value:
        return "idea_analysis"
    return "business_model"


def pause_for_review(reason: str) -> dict[str, Any]:
    """Return a delta that marks the graph as paused for founder review."""
    return {
        "human_review_required": True,
        "human_review_action": None,
        "human_review_notes": reason,
    }
