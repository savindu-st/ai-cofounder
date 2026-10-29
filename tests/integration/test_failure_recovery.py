"""Integration Test Scenario C: Failure Recovery and HITL Resume."""

import asyncio

from langgraph.checkpoint.memory import MemorySaver

from shared.contracts.critic import CriticValidationOutput
from shared.contracts.idea import FounderInput
from shared.enums.confidence_level import ValidationStatus
from shared.enums.workflow_status import WorkflowStage
from services.orchestrator.app.orchestration.coordinator import WorkflowCoordinator


def _founder():
    return FounderInput(
        startup_idea="Autonomous customer feedback analysis platform",
        target_market="B2B SaaS Product Teams",
        target_geography="Global",
        budget=40000.0,
        timeline_months=6,
        goals="Validate and launch MVP",
    )


def test_node_failure_marks_venture_failed(monkeypatch):
    async def broken_idea_analysis(*args, **kwargs):
        raise RuntimeError("provider outage")

    import services.business_intelligence.app.interface as bi_interface
    monkeypatch.setattr(bi_interface, "run_idea_analysis", broken_idea_analysis)

    coordinator = WorkflowCoordinator(checkpointer=MemorySaver(), enable_hitl=False)

    async def _run():
        try:
            await coordinator.start_workflow(
                venture_id="test-venture-failure-c-001",
                founder_input=_founder(),
                run_sync=True,
            )
        except RuntimeError:
            pass
        return await coordinator.get_state("test-venture-failure-c-001")

    state = asyncio.run(_run())
    assert state is not None
    assert state.current_stage == WorkflowStage.FAILED
    assert any("provider outage" in warning for warning in state.warnings)


def test_hitl_pause_and_resume_records_real_action(monkeypatch):
    async def always_requires_research(market, idea):
        return CriticValidationOutput(
            status=ValidationStatus.RESEARCH_REQUIRED,
            confidence_score=0.3,
            unsupported_claims=["Unverified market claim"],
            verified_sources_count=0,
            feedback_notes="Research remains insufficient.",
        )

    import services.research.app.interface as research_interface
    monkeypatch.setattr(
        research_interface,
        "run_critic_validation",
        always_requires_research,
    )

    coordinator = WorkflowCoordinator(checkpointer=MemorySaver(), enable_hitl=True)
    venture_id = "test-venture-hitl-c-002"

    async def _run():
        paused = await coordinator.start_workflow(
            venture_id=venture_id,
            founder_input=_founder(),
            run_sync=True,
        )
        config = {"configurable": {"thread_id": venture_id}}
        snapshot = coordinator.workflow.get_state(config)
        resumed = await coordinator.resume_workflow(
            venture_id=venture_id,
            action="PROCEED_ANYWAY",
            feedback="Founder accepts remaining research risk.",
            run_sync=True,
        )
        return paused, snapshot, resumed

    paused, snapshot, resumed = asyncio.run(_run())

    assert paused.human_review_required is True
    assert "human_review" in snapshot.next
    assert resumed.current_stage == WorkflowStage.COMPLETED
    assert resumed.human_review_required is False
    assert resumed.human_review_action == "PROCEED_ANYWAY"
    assert resumed.human_review_notes == "Founder accepts remaining research risk."
    assert resumed.final_roadmap is not None
