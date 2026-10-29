import asyncio
from types import SimpleNamespace

import pytest

from shared.contracts.idea import FounderInput
from shared.contracts.venture_state import VentureState
from shared.enums.workflow_status import WorkflowStage
from services.orchestrator.app.orchestration import failure_handler as fh
from services.orchestrator.app.orchestration.failure_handler import (
    NodeExecutionError,
    NodeTimeoutError,
    failure_state_updates,
    invoke_with_timeout,
    run_node_operation,
)
from services.orchestrator.app.orchestration.retry_handler import RetryConfig


def _state():
    return VentureState(
        venture_id="failure-test",
        founder_input=FounderInput(startup_idea="A sufficiently long startup idea", target_market="Tech"),
    )


def test_invoke_with_timeout_raises_node_timeout():
    async def slow():
        await asyncio.sleep(0.05)

    with pytest.raises(NodeTimeoutError):
        asyncio.run(invoke_with_timeout(slow, timeout_seconds=0.001))


def test_run_node_operation_retries_then_succeeds():
    attempts = {"count": 0}

    async def flaky():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("transient")
        return "done"

    result = asyncio.run(
        run_node_operation(
            flaky,
            node_name="test_node",
            retry_config=RetryConfig(max_attempts=2, base_delay=0, jitter=False),
        )
    )
    assert result == "done"
    assert attempts["count"] == 2


def test_run_node_operation_wraps_exhausted_failure():
    async def broken():
        raise RuntimeError("permanent")

    with pytest.raises(NodeExecutionError) as exc_info:
        asyncio.run(
            run_node_operation(
                broken,
                node_name="test_node",
                retry_config=RetryConfig(max_attempts=2, base_delay=0, jitter=False),
            )
        )
    assert exc_info.value.node_name == "test_node"
    assert "permanent" in str(exc_info.value.cause)


def test_failure_state_updates_marks_failed_and_warns():
    delta = failure_state_updates(_state(), "idea_analysis", RuntimeError("boom"))
    assert delta["current_stage"] == WorkflowStage.FAILED
    assert any("idea_analysis failed" in warning for warning in delta["warnings"])


def test_recovery_reports_paused_ventures_without_auto_resume(monkeypatch):
    state = _state()
    state.current_stage = WorkflowStage.MARKET_RESEARCH
    venture = SimpleNamespace(id=state.venture_id)

    class Workflow:
        def get_state(self, config):
            return SimpleNamespace(next=("human_review",))

    class Coordinator:
        workflow = Workflow()

        async def resume_workflow(self, **kwargs):
            raise AssertionError("Paused venture must not be auto-resumed")

        async def start_workflow(self, **kwargs):
            raise AssertionError("Paused venture must not be restarted")

    async def fake_incomplete(session, limit=25):
        return [venture]

    async def fake_get_state(venture_id, session=None):
        return state

    monkeypatch.setattr(fh, "get_incomplete_ventures", fake_incomplete)
    monkeypatch.setattr(fh, "get_venture_state", fake_get_state)

    recovered = asyncio.run(fh.recover_incomplete_ventures(Coordinator(), session=object()))
    assert recovered == [state.venture_id]
    assert state.human_review_required is True


def test_recovery_resumes_active_checkpoints(monkeypatch):
    state = _state()
    state.current_stage = WorkflowStage.MARKET_RESEARCH
    venture = SimpleNamespace(id=state.venture_id)
    calls = []

    class Workflow:
        def get_state(self, config):
            return SimpleNamespace(next=("critic_validation",))

    class Coordinator:
        workflow = Workflow()

        async def resume_checkpoint(self, **kwargs):
            calls.append(kwargs)

        async def resume_workflow(self, **kwargs):
            raise AssertionError("Should resume existing checkpoint directly")

        async def start_workflow(self, **kwargs):
            raise AssertionError("Should resume existing checkpoint")

    async def fake_incomplete(session, limit=25):
        return [venture]

    async def fake_get_state(venture_id, session=None):
        return state

    monkeypatch.setattr(fh, "get_incomplete_ventures", fake_incomplete)
    monkeypatch.setattr(fh, "get_venture_state", fake_get_state)

    recovered = asyncio.run(fh.recover_incomplete_ventures(Coordinator(), session=object()))
    assert recovered == [state.venture_id]
    assert calls and calls[0]["venture_id"] == state.venture_id
