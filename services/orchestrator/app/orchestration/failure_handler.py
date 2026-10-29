"""Failure isolation, node timeouts, and startup crash recovery."""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
from functools import partial
from typing import Any, Callable, Optional

from sqlalchemy import select

from shared.contracts.venture_state import VentureState
from shared.enums.workflow_status import WorkflowStage
from services.orchestrator.app.orchestration.event_bus import publish_event
from services.orchestrator.app.orchestration.human_review import HumanReviewAction
from services.orchestrator.app.orchestration.retry_handler import (
    RetryConfig,
    RetryExhaustedError,
    retry_async,
)
from services.orchestrator.app.state.checkpoint import get_thread_config
from services.orchestrator.app.state.state_manager import (
    get_venture_state,
    save_venture_state,
)
from database.models.venture import Venture

logger = logging.getLogger(__name__)

DEFAULT_NODE_TIMEOUT_SECONDS = 120.0
TERMINAL_STAGES = {
    WorkflowStage.COMPLETED.value,
    WorkflowStage.FAILED.value,
    "ABORTED",
}


class NodeTimeoutError(TimeoutError):
    """Raised when a single node exceeds its execution deadline."""


class NodeExecutionError(RuntimeError):
    """Controlled node failure that keeps the underlying cause for diagnostics."""

    def __init__(self, node_name: str, cause: BaseException):
        self.node_name = node_name
        self.cause = cause
        super().__init__(f"Node '{node_name}' failed: {cause}")


def node_timeout_seconds() -> float:
    try:
        return max(0.01, float(os.getenv("NODE_TIMEOUT_SECONDS", DEFAULT_NODE_TIMEOUT_SECONDS)))
    except (TypeError, ValueError):
        return DEFAULT_NODE_TIMEOUT_SECONDS


async def invoke_with_timeout(
    operation: Callable[..., Any],
    *args: Any,
    timeout_seconds: Optional[float] = None,
    **kwargs: Any,
) -> Any:
    """Invoke a sync or async operation under an asyncio timeout."""
    timeout = timeout_seconds or node_timeout_seconds()
    if inspect.iscoroutinefunction(operation):
        awaitable = operation(*args, **kwargs)
    else:
        awaitable = asyncio.to_thread(partial(operation, *args, **kwargs))

    try:
        return await asyncio.wait_for(awaitable, timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise NodeTimeoutError(
            f"Operation '{getattr(operation, '__name__', 'operation')}' timed out after {timeout:.1f}s."
        ) from exc


async def run_node_operation(
    operation: Callable[..., Any],
    *args: Any,
    node_name: str,
    timeout_seconds: Optional[float] = None,
    retry_config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[BaseException, int, float], Any]] = None,
    **kwargs: Any,
) -> Any:
    """Execute one node operation with timeout + exponential backoff + sandboxing."""

    async def _attempt() -> Any:
        return await invoke_with_timeout(
            operation,
            *args,
            timeout_seconds=timeout_seconds,
            **kwargs,
        )

    try:
        return await retry_async(
            _attempt,
            config=retry_config or RetryConfig(max_attempts=2, base_delay=0.1, max_delay=1.0),
            operation_name=node_name,
            on_retry=on_retry,
        )
    except RetryExhaustedError as exc:
        raise NodeExecutionError(node_name, exc.last_error) from exc
    except Exception as exc:
        raise NodeExecutionError(node_name, exc) from exc


def failure_state_updates(state: VentureState, node_name: str, error: BaseException) -> dict[str, Any]:
    """Return a standardized terminal delta for a failed node."""
    warnings = list(state.warnings)
    warning = f"{node_name} failed: {error}"
    if warning not in warnings:
        warnings.append(warning)
    return {
        "current_stage": WorkflowStage.FAILED,
        "warnings": warnings,
    }


async def get_incomplete_ventures(session: Any, limit: int = 25) -> list[Venture]:
    """Return persisted ventures that never reached a terminal stage."""
    if session is None:
        return []
    stmt = (
        select(Venture)
        .where(Venture.status.notin_(TERMINAL_STAGES))
        .order_by(Venture.updated_at.asc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _resume_or_restart(coordinator: Any, venture_id: str, state: VentureState, session: Any) -> None:
    config = get_thread_config(venture_id)
    snapshot = coordinator.workflow.get_state(config)
    next_nodes = tuple(getattr(snapshot, "next", ()) or ())

    if "human_review" in next_nodes:
        state.human_review_required = True
        await save_venture_state(state)
        await publish_event(
            venture_id=venture_id,
            stage=state.current_stage,
            event_type="HITL_REQUIRED",
            progress_pct=0,
            message="Recovered paused venture awaiting founder review.",
            data={"venture_id": venture_id, "recovery": True},
        )
        return

    if next_nodes:
        resume_checkpoint = getattr(coordinator, "resume_checkpoint", None)
        if callable(resume_checkpoint):
            await resume_checkpoint(venture_id=venture_id, session=session, run_sync=False)
        else:
            await coordinator.resume_workflow(
                venture_id=venture_id,
                action=HumanReviewAction.PROCEED_ANYWAY.value,
                session=session,
                run_sync=False,
            )
        return

    await coordinator.start_workflow(
        venture_id=venture_id,
        founder_input=state.founder_input,
        session=session,
        run_sync=False,
    )


async def recover_incomplete_ventures(
    coordinator: Any,
    session: Any = None,
    limit: int = 25,
) -> list[str]:
    """Scan PostgreSQL for non-terminal ventures and resume from their checkpoint.

    Paused HITL ventures are surfaced again instead of being auto-approved.
    Recovery is best-effort: one corrupt venture must not block server startup.
    """
    if session is None:
        return []

    try:
        ventures = await get_incomplete_ventures(session, limit=limit)
    except Exception as exc:
        logger.warning("[StartupRecovery] Could not query incomplete ventures: %s", exc)
        return []

    recovered: list[str] = []
    for venture in ventures:
        venture_id = venture.id
        try:
            state = await get_venture_state(venture_id, session)
            if state is None or state.current_stage.value in TERMINAL_STAGES:
                continue
            await _resume_or_restart(coordinator, venture_id, state, session)
            recovered.append(venture_id)
            logger.info("[StartupRecovery] Scheduled recovery for venture %s", venture_id)
        except Exception as exc:
            logger.warning("[StartupRecovery] Failed to recover venture %s: %s", venture_id, exc)

    return recovered
