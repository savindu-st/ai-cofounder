"""Orchestrator REST API Routes.

Implements venture pipeline management, state hydration, and
Human-in-the-Loop (HITL) review actions via WorkflowCoordinator.
"""

import re
from typing import Optional, Literal
from fastapi import APIRouter, HTTPException, Response, status
from starlette.concurrency import run_in_threadpool
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

    try:
        resumed_state = await coordinator.resume_workflow(
            venture_id=venture_id,
            action=review.action,
            feedback=review.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return {
        "venture_id": venture_id,
        "status": "ABORTED" if review.action == "ABORT" else "RESUMED",
        "action_taken": review.action,
        "current_stage": resumed_state.current_stage.value if resumed_state else "UNKNOWN",
        "human_review_required": (
            resumed_state.human_review_required if resumed_state else False
        ),
    }


def _safe_filename(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return slug or "startup-roadmap"


async def _roadmap_for_export(venture_id: str):
    state = await coordinator.get_state(venture_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Venture with ID '{venture_id}' not found."
        )
    if state.final_roadmap is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Venture '{venture_id}' has no completed roadmap to export."
        )
    return state.final_roadmap


@router.get("/ventures/{venture_id}/export/pdf")
async def export_venture_pdf(venture_id: str):
    """Download the completed venture roadmap as an executive PDF."""
    roadmap = await _roadmap_for_export(venture_id)
    from services.marketing_output.app.export.pdf_exporter import generate_pdf

    content = await run_in_threadpool(generate_pdf, roadmap)
    filename = f"{_safe_filename(roadmap.venture_name)}-roadmap.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/ventures/{venture_id}/export/docx")
async def export_venture_docx(venture_id: str):
    """Download the completed venture roadmap as an editable Word document."""
    roadmap = await _roadmap_for_export(venture_id)
    from services.marketing_output.app.export.docx_exporter import generate_docx

    content = await run_in_threadpool(generate_docx, roadmap)
    filename = f"{_safe_filename(roadmap.venture_name)}-roadmap.docx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/ventures/{venture_id}/export/html")
async def export_venture_html(venture_id: str):
    """Download the completed venture roadmap as a standalone responsive HTML report."""
    roadmap = await _roadmap_for_export(venture_id)
    from services.marketing_output.app.export.roadmap_renderer import render_roadmap_html

    content = await run_in_threadpool(render_roadmap_html, roadmap)
    filename = f"{_safe_filename(roadmap.venture_name)}-roadmap.html"
    return Response(
        content=content,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
