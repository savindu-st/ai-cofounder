"""Workflow Coordinator.

Coordinates execution, background task scheduling, state persistence,
and human-in-the-loop interactions for the venture creation LangGraph workflow.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from shared.contracts.idea import FounderInput
from shared.contracts.venture_state import VentureState
from shared.enums.workflow_status import WorkflowStage
from services.orchestrator.app.graph.workflow import build_venture_workflow
from services.orchestrator.app.state.checkpoint import get_checkpointer, get_thread_config
from services.orchestrator.app.state.venture_state import create_initial_venture_state
from services.orchestrator.app.state.state_manager import (
    save_venture_state,
    get_venture_state,
)
from services.orchestrator.app.orchestration.event_bus import publish_event

logger = logging.getLogger(__name__)


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
        """Starts a new venture analysis workflow.
        
        Args:
            venture_id: Unique identifier for the venture.
            raw_idea: Optional original pitch or idea description.
            founder_input: Optional FounderInput contract instance.
            user_id: Optional user identifier.
            session: Optional database session.
            run_sync: If True, awaits workflow execution instead of background task.
            
        Returns:
            VentureState instance (initial state if async, terminal state if sync).
        """
        initial_state = create_initial_venture_state(
            venture_id=venture_id,
            raw_idea=raw_idea,
            founder_input=founder_input,
        )
        await save_venture_state(initial_state, session)

        await publish_event(
            venture_id=venture_id,
            event_type="workflow_started",
            payload={
                "venture_id": venture_id,
                "current_stage": initial_state.current_stage.value,
                "message": "Workflow started successfully",
            },
        )

        if run_sync:
            return await self._execute_graph(venture_id, initial_state, session)
        else:
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

            if isinstance(result, dict):
                updated_state = VentureState.model_validate(result)
            elif isinstance(result, VentureState):
                updated_state = result
            else:
                updated_state = await get_venture_state(venture_id, session) or input_data

            await save_venture_state(updated_state, session)

            # Check if workflow reached human_review interrupt
            state_snapshot = self.workflow.get_state(config)
            if state_snapshot and state_snapshot.next:
                if "human_review" in state_snapshot.next:
                    await publish_event(
                        venture_id=venture_id,
                        event_type="hitl_required",
                        payload={
                            "venture_id": venture_id,
                            "current_stage": updated_state.current_stage.value,
                            "message": "Human review required to proceed.",
                        },
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
                event_type="workflow_completed",
                progress_pct=100,
                message="Workflow completed successfully.",
                data={
                    "venture_id": venture_id,
                    "current_stage": updated_state.current_stage.value,
                    "confidence_score": overall_confidence,
                },
            )
            return updated_state

        except Exception as e:
            logger.exception(f"Error executing venture workflow {venture_id}: {e}")
            current_state = await get_venture_state(venture_id, session)
            if current_state:
                current_state.current_stage = WorkflowStage.FAILED
                current_state.warnings.append(str(e))
                await save_venture_state(current_state, session)

            await publish_event(
                venture_id=venture_id,
                stage=WorkflowStage.FAILED,
                event_type="workflow_failed",
                progress_pct=0,
                message=f"Workflow failed: {str(e)}",
                data={"venture_id": venture_id, "error": str(e)},
            )
            raise
        finally:
            self._active_tasks.pop(venture_id, None)

    async def resume_workflow(
        self,
        venture_id: str,
        human_approved: bool = True,
        feedback: Optional[str] = None,
        session: Optional[AsyncSession] = None,
        run_sync: bool = False,
    ) -> VentureState:
        """Resumes a paused workflow at the human review checkpoint.
        
        Args:
            venture_id: Target venture identifier.
            human_approved: Decision indicating whether the venture is approved.
            feedback: Optional feedback string for refinement.
            session: Optional database session.
            run_sync: Whether to await completion or run async.
        """
        config = get_thread_config(venture_id)

        # Update state values for human review
        update_payload: Dict[str, Any] = {
            "human_approved": human_approved,
        }
        if feedback:
            update_payload["human_feedback"] = feedback

        self.workflow.update_state(config, update_payload)

        await publish_event(
            venture_id=venture_id,
            event_type="hitl_resumed",
            payload={"venture_id": venture_id, "approved": human_approved},
        )

        if run_sync:
            return await self._execute_graph(venture_id, None, session)
        else:
            task = asyncio.create_task(self._execute_graph(venture_id, None, session))
            self._active_tasks[venture_id] = task
            current_state = await get_venture_state(venture_id, session)
            return current_state or VentureState(venture_id=venture_id, raw_idea="")

    async def get_state(
        self,
        venture_id: str,
        session: Optional[AsyncSession] = None,
    ) -> Optional[VentureState]:
        """Retrieves the latest venture state."""
        return await get_venture_state(venture_id, session)


# Global coordinator instance
coordinator = WorkflowCoordinator()
