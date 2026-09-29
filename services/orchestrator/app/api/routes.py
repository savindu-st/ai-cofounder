"""Orchestrator REST API Routes.

Implements venture pipeline management, state hydration, and
Human-in-the-Loop (HITL) review actions via WorkflowCoordinator.
"""

from typing import Optional, Literal
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from shared.contracts.idea import FounderInput
from shared.contracts.venture_state import VentureState
from shared.utils.ids import generate_venture_id
from services.orchestrator.app.orchestration.coordinator import coordinator

router = APIRouter()


class HumanReviewPayload(BaseModel):
    action: Literal["PROCEED_ANYWAY", "OVERRIDE_ASSUMPTIONS", "ABORT"]
    notes: Optional[str] = Field(default=None, description="Optional founder rationale or parameter override notes")


@router.post("/ventures/start", status_code=status.HTTP_201_CREATED)
async def start_venture(input_data: FounderInput):
    """Initializes a new venture state and kicks off the multi-agent pipeline."""
    venture_id = generate_venture_id()
    initial_state = await coordinator.start_workflow(
        venture_id=venture_id,
        founder_input=input_data,
    )
    return {
        "venture_id": venture_id,
        "status": initial_state.current_stage,
        "message": "Venture workflow initialized and running."
    }


@router.get("/ventures/{venture_id}", response_model=VentureState)
async def get_venture_state(venture_id: str):
    """State Hydration Endpoint: Returns the latest durable VentureState snapshot."""
    state = await coordinator.get_state(venture_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Venture with ID '{venture_id}' not found."
        )
    return state


@router.post("/ventures/{venture_id}/review")
async def submit_human_review(venture_id: str, review: HumanReviewPayload):
    """Human-in-the-Loop (HITL) Resume API.
    
    Allows founder to unpause the pipeline when human review is required.
    Actions:
    - PROCEED_ANYWAY: Accept warnings and advance to next stage.
    - OVERRIDE_ASSUMPTIONS: Incorporate founder notes and re-run active stage.
    - ABORT: Terminate pipeline as FAILED.
    """
    state = await coordinator.get_state(venture_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Venture with ID '{venture_id}' not found."
        )

    approved = (review.action != "ABORT")
    resumed_state = await coordinator.resume_workflow(
        venture_id=venture_id,
        human_approved=approved,
        feedback=review.notes,
    )

    return {
        "venture_id": venture_id,
        "status": "ABORTED" if review.action == "ABORT" else "RESUMED",
        "action_taken": review.action,
        "current_stage": resumed_state.current_stage if resumed_state else "UNKNOWN"
    }
