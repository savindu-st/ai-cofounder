"""Workflow Coordinator.

Coordinates execution, background task scheduling, state persistence,
and human-in-the-loop interactions for the venture creation LangGraph workflow.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from shared.contracts.idea import FounderInput
from shared.contracts.venture_state import VentureState
from shared.enums.workflow_status import WorkflowStage
from services.orchestrator.app.graph.workflow import build_venture_workflow
from services.orchestrator.app.orchestration.event_bus import publish_event
from services.orchestrator.app.orchestration.human_review import (
    HumanReviewAction,
    apply_human_review,
    normalize_review_action,
)
from services.orchestrator.app.state.checkpoint import get_checkpointer, get_thread_config
from services.orchestrator.app.state.state_manager import (
    get_venture_state,
    save_venture_state,
)
from services.orchestrator.app.state.venture_state import create_initial_venture_state

logger = logging.getLogger(__name__)

TERMINAL_STAGES = {WorkflowStage.COMPLETED, WorkflowStage.FAILED}


class WorkflowCoordinator:
    """Orchestrates asynchronous execution of the LangGraph venture workflow."""

    def __init__(self, checkpointer: Optional[Any] = None, enable_hitl: bool = True):
        self.checkpointer = checkpointer or get_checkpointer()
        self.enable_hitl = enable_hitl
        self.workflow = build_venture_workflow(
            checkpointer=self.checkpointer,
            enable_hitl_interrupt=self.enable_hitl,
        )
        self._active_tasks: Dict[str, asyncio.Task] = {}

    async def start_workflow(
        self,
        venture_id: str,
        raw_idea: Optional[str] = None,
        founder_input: Optional[FounderInput] = None,
        user_id: Optional[str] = None,
        session: Optional[AsyncSession] = None,
        run_sync: bool = False,
    ) -> VentureState:
        """Starts a new venture analysis workflow."""
        initial_state = create_initial_venture_state(
            venture_id=venture_id,
            raw_idea=raw_idea,
            founder_input=founder_input,
        )
        await save_venture_state(initial_state, session)

        await publish_event(
            venture_id=venture_id,
            stage=initial_state.current_stage,
            event_type="WORKFLOW_STARTED",
            progress_pct=0,
            message="Workflow started successfully.",
            data={"venture_id": venture_id, "current_stage": initial_state.current_stage.value},
        )

        if run_sync:
            return await self._execute_graph(venture_id, initial_state, session)

        task = asyncio.create_task(self._execute_graph(venture_id, initial_state, session))
        self._active_tasks[venture_id] = task
        return initial_state

    async def _execute_graph(
        self,
        venture_id: str,
        input_data: Any,
        session: Optional[AsyncSession] = None,
    ) -> VentureState:
        """Internal worker executing the LangGraph graph with state persistence."""
        config = get_thread_config(venture_id)
        try:
            result = await self.workflow.ainvoke(input_data, config=config)
            updated_state = await self._coerce_state(venture_id, result, input_data)

            snapshot = self.workflow.get_state(config)
            next_nodes = tuple(getattr(snapshot, "next", ()) or ())
            if "human_review" in next_nodes:
                updated_state.human_review_required = True
                await save_venture_state(updated_state, session)
                await publish_event(
                    venture_id=venture_id,
                    stage=updated_state.current_stage,
                    event_type="HITL_REQUIRED",
                    progress_pct=0,
                    message="Human review required to proceed.",
                    data={
                        "venture_id": venture_id,
                        "current_stage": updated_state.current_stage.value,
                        "warnings": updated_state.warnings[-5:],
                    },
                )
                return updated_state

            await save_venture_state(updated_state, session)

            if updated_state.current_stage == WorkflowStage.FAILED:
                await publish_event(
                    venture_id=venture_id,
                    stage=WorkflowStage.FAILED,
                    event_type="WORKFLOW_FAILED",
                    progress_pct=0,
                    message="Workflow stopped in a failed state.",
                    data={"venture_id": venture_id},
                )
                return updated_state

            overall_confidence = (
                updated_state.final_roadmap.overall_confidence_score
                if updated_state.final_roadmap
                else 0.0
            )
            await publish_event(
                venture_id=venture_id,
                stage=updated_state.current_stage,
                event_type="WORKFLOW_COMPLETED",
                progress_pct=100,
                message="Workflow completed successfully.",
                data={
                    "venture_id": venture_id,
                    "current_stage": updated_state.current_stage.value,
                    "confidence_score": overall_confidence,
                },
            )
            return updated_state

        except asyncio.CancelledError:
            await self._mark_failed(venture_id, "Workflow cancelled.", session, publish=False)
            raise
        except Exception as exc:
            logger.exception("Error executing venture workflow %s: %s", venture_id, exc)
            await self._mark_failed(venture_id, str(exc), session, publish=True)
            raise
        finally:
            current_task = asyncio.current_task()
            if self._active_tasks.get(venture_id) is current_task:
                self._active_tasks.pop(venture_id, None)

    async def _coerce_state(self, venture_id: str, result: Any, fallback: Any) -> VentureState:
        if isinstance(result, VentureState):
            return result
        if isinstance(result, dict):
            return VentureState.model_validate(result)
        existing = await get_venture_state(venture_id)
        if existing is not None:
            return existing
        if isinstance(fallback, VentureState):
            return fallback
        return create_initial_venture_state(venture_id=venture_id)

    async def _mark_failed(
        self,
        venture_id: str,
        error: str,
        session: Optional[AsyncSession],
        publish: bool,
    ) -> None:
        current_state = await get_venture_state(venture_id, session)
        if current_state is None:
            return
        current_state.current_stage = WorkflowStage.FAILED
        if error not in current_state.warnings:
            current_state.warnings.append(error)
        await save_venture_state(current_state, session)
        if publish:
            await publish_event(
                venture_id=venture_id,
                stage=WorkflowStage.FAILED,
                event_type="WORKFLOW_FAILED",
                progress_pct=0,
                message=f"Workflow failed: {error}",
                data={"venture_id": venture_id, "error": error},
            )

    async def resume_workflow(
        self,
        venture_id: str,
        human_approved: bool = True,
        feedback: Optional[str] = None,
        action: Optional[str] = None,
        session: Optional[AsyncSession] = None,
        run_sync: bool = False,
    ) -> VentureState:
        """Apply a founder review action and resume a paused workflow when needed."""
        normalized = normalize_review_action(action, human_approved=human_approved)
        state = await get_venture_state(venture_id, session)
        if state is None:
            raise ValueError(f"Venture '{venture_id}' not found.")

        if normalized == HumanReviewAction.ABORT:
            task = self._active_tasks.get(venture_id)
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

            updates = apply_human_review(state, normalized, feedback)
            aborted_state = state.model_copy(update=updates)
            await save_venture_state(aborted_state, session)
            await publish_event(
                venture_id=venture_id,
                stage=WorkflowStage.FAILED,
                event_type="WORKFLOW_FAILED",
                progress_pct=0,
                message="Venture aborted by founder.",
                data={"venture_id": venture_id, "action": normalized.value},
            )
            return aborted_state

        # If a background run is still in flight, let it reach its interrupt/terminal
        # checkpoint before mutating the thread state.
        active_task = self._active_tasks.get(venture_id)
        if active_task is not None and not active_task.done():
            try:
                await active_task
            except Exception:
                pass
            state = await get_venture_state(venture_id, session) or state

        config = get_thread_config(venture_id)
        snapshot = self.workflow.get_state(config)
        next_nodes = tuple(getattr(snapshot, "next", ()) or ())

        if state.current_stage in TERMINAL_STAGES and "human_review" not in next_nodes:
            # Preserve a terminal outcome while still recording the founder action.
            state.human_review_required = False
            state.human_review_action = normalized.value
            state.human_review_notes = feedback
            await save_venture_state(state, session)
            return state

        updates = apply_human_review(state, normalized, feedback)
        if "human_review" in next_nodes:
            self.workflow.update_state(config, updates, as_node="human_review")
        else:
            state = state.model_copy(update=updates)
            await save_venture_state(state, session)

        await publish_event(
            venture_id=venture_id,
            stage=WorkflowStage.REPLANNING,
            event_type="HITL_RESUMED",
            progress_pct=0,
            message=f"Founder review action accepted: {normalized.value}.",
            data={"venture_id": venture_id, "action": normalized.value},
        )

        if "human_review" not in next_nodes:
            return state

        if run_sync:
            return await self._execute_graph(venture_id, None, session)

        task = asyncio.create_task(self._execute_graph(venture_id, None, session))
        self._active_tasks[venture_id] = task
        return await get_venture_state(venture_id, session) or state

    async def resume_checkpoint(
        self,
        venture_id: str,
        session: Optional[AsyncSession] = None,
        run_sync: bool = False,
    ) -> VentureState:
        """Resume a non-HITL checkpoint after a process crash."""
        if run_sync:
            return await self._execute_graph(venture_id, None, session)

        task = asyncio.create_task(self._execute_graph(venture_id, None, session))
        self._active_tasks[venture_id] = task
        state = await get_venture_state(venture_id, session)
        if state is None:
            raise ValueError(f"Venture '{venture_id}' not found.")
        return state

    async def get_state(
        self,
        venture_id: str,
        session: Optional[AsyncSession] = None,
    ) -> Optional[VentureState]:
        """Retrieves the latest venture state."""
        return await get_venture_state(venture_id, session)


# Global coordinator instance
coordinator = WorkflowCoordinator()
