"""Integration Test Scenario B: Targeted Re-planning Loop."""

import asyncio

from langgraph.checkpoint.memory import MemorySaver

from shared.contracts.critic import CriticValidationOutput
from shared.contracts.idea import FounderInput
from shared.contracts.venture_state import VentureState
from shared.enums.confidence_level import ValidationStatus
from shared.enums.workflow_status import WorkflowStage
from services.orchestrator.app.graph.workflow import build_venture_workflow
from services.orchestrator.app.state.checkpoint import get_thread_config
from services.orchestrator.app.state.venture_state import create_initial_venture_state


def test_replanning_path(monkeypatch):
    """Research-required critique triggers market retry, then completes on VALID."""
    calls = {"critic": 0}

    async def fake_critic(market, idea):
        calls["critic"] += 1
        if calls["critic"] == 1:
            return CriticValidationOutput(
                status=ValidationStatus.RESEARCH_REQUIRED,
                confidence_score=0.42,
                unsupported_claims=["Missing primary citation for market size"],
                verified_sources_count=1,
                feedback_notes="Add a verified primary source for the TAM estimate.",
            )
        return CriticValidationOutput(
            status=ValidationStatus.VALID,
            confidence_score=0.9,
            unsupported_claims=[],
            verified_sources_count=3,
            feedback_notes="Validation passed.",
        )

    import services.research.app.interface as research_interface
    monkeypatch.setattr(research_interface, "run_critic_validation", fake_critic)

    async def _run():
        venture_id = "test-venture-replan-b-001"
        initial_state = create_initial_venture_state(
            venture_id=venture_id,
            founder_input=FounderInput(
                startup_idea="AI-powered code review assistant for engineering teams",
                target_market="Developer Tools",
                target_geography="Global",
                budget=75000.0,
                timeline_months=6,
                goals="Reach 100 paying teams",
            ),
        )
        workflow = build_venture_workflow(
            checkpointer=MemorySaver(),
            enable_hitl_interrupt=False,
        )
        result = await workflow.ainvoke(initial_state, config=get_thread_config(venture_id))
        return result if isinstance(result, VentureState) else VentureState.model_validate(result)

    final_state = asyncio.run(_run())

    assert calls["critic"] == 2
    assert final_state.current_stage == WorkflowStage.COMPLETED
    assert final_state.replan_count == 1
    assert final_state.market_replan_count == 1
    assert final_state.replan_target == "market_research"
    assert len(final_state.critique_history) == 2
    assert any("market_research required" in warning for warning in final_state.warnings)
    assert final_state.final_roadmap is not None
