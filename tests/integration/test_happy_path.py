"""Integration Test Scenario A: Happy Path.

Executes the complete 7-node LangGraph autonomous venture creation pipeline end-to-end:
START -> idea_analysis -> market_research -> critic_validation (PASS)
      -> business_model -> revenue_estimation (PASS) -> marketing_plan
      -> roadmap_synthesis -> COMPLETED / END
"""

import asyncio
from langgraph.checkpoint.memory import MemorySaver

from shared.contracts.idea import FounderInput
from shared.contracts.venture_state import VentureState
from shared.enums.confidence_level import ValidationStatus
from shared.enums.workflow_status import WorkflowStage
from services.orchestrator.app.graph.workflow import build_venture_workflow
from services.orchestrator.app.state.checkpoint import get_thread_config
from services.orchestrator.app.state.venture_state import create_initial_venture_state
from services.orchestrator.app.orchestration.coordinator import coordinator


def test_happy_path_workflow_direct():
    """Validates the compiled LangGraph StateGraph executes all 7 nodes linearly to completion."""
    async def _run():
        venture_id = "test-venture-hp-direct-001"
        founder_input = FounderInput(
            startup_idea="An AI-powered autonomous code review agent that spots edge-case logic bugs",
            target_market="Software Engineering Teams",
            target_geography="Global",
            budget=50000.0,
            timeline_months=6,
            goals="Acquire 100 paying engineering teams",
        )

        initial_state = create_initial_venture_state(
            venture_id=venture_id,
            founder_input=founder_input,
        )

        workflow = build_venture_workflow(
            checkpointer=MemorySaver(),
            enable_hitl_interrupt=False,
        )

        config = get_thread_config(venture_id)
        raw_output = await workflow.ainvoke(initial_state, config=config)

        # Reconstitute typed VentureState from LangGraph delta dictionary if needed
        if isinstance(raw_output, dict):
            final_state = VentureState.model_validate(raw_output)
        else:
            final_state = raw_output

        # 1. State machine termination status
        assert final_state.current_stage == WorkflowStage.COMPLETED

        # 2. Node 1: Idea Analysis
        assert final_state.idea_analysis is not None
        assert "code review agent" in final_state.idea_analysis.problem_statement
        assert final_state.idea_analysis.confidence_score > 0.7

        # 3. Node 2: Market Research
        assert final_state.market_research is not None
        assert len(final_state.market_research.competitor_landscape) >= 2
        assert final_state.market_research.tam_estimate > final_state.market_research.sam_estimate
        assert final_state.market_research.sam_estimate > final_state.market_research.som_estimate

        # 4. Node 3: Critic Validation
        assert final_state.market_validation is not None
        assert final_state.market_validation.status == ValidationStatus.VALID
        assert final_state.market_validation.verified_sources_count >= 2
        assert len(final_state.critique_history) >= 1

        # 5. Node 4: Business Model Canvas
        assert final_state.business_model is not None
        assert len(final_state.business_model.canvas.value_propositions) > 0
        assert len(final_state.business_model.canvas.revenue_streams) > 0

        # 6. Node 5: Revenue Estimation
        assert final_state.revenue_estimation is not None
        assert final_state.revenue_estimation.tam_sam_som_valid is True
        assert len(final_state.revenue_estimation.scenarios) == 3

        # 7. Node 6: Marketing Plan
        assert final_state.marketing_plan is not None
        assert len(final_state.marketing_plan.priority_channels) > 0
        assert len(final_state.marketing_plan.gtm_90_day_plan) > 0

        # 8. Node 7: Final Roadmap Synthesis
        assert final_state.final_roadmap is not None
        assert final_state.final_roadmap.venture_id == venture_id
        assert final_state.final_roadmap.overall_confidence_score >= 0.70
        assert len(final_state.final_roadmap.executive_summary) > 20

    asyncio.run(_run())


def test_happy_path_workflow_coordinator():
    """Validates the WorkflowCoordinator running sync end-to-end with state persistence."""
    async def _run():
        venture_id = "test-venture-hp-coord-002"
        founder_input = FounderInput(
            startup_idea="Automated micro-SaaS monitoring and incident triage assistant",
            target_market="DevOps and SRE Engineers",
            target_geography="North America",
            budget=25000.0,
            timeline_months=3,
            goals="Launch MVP and onboard 50 beta teams",
        )

        final_state = await coordinator.start_workflow(
            venture_id=venture_id,
            founder_input=founder_input,
            run_sync=True,
        )

        assert final_state.current_stage == WorkflowStage.COMPLETED
        assert final_state.final_roadmap is not None
        assert final_state.final_roadmap.overall_confidence_score > 0.0

        # Check hydration from state manager cache
        cached_state = await coordinator.get_state(venture_id)
        assert cached_state is not None
        assert cached_state.venture_id == venture_id
        assert cached_state.current_stage == WorkflowStage.COMPLETED
        assert cached_state.final_roadmap is not None

    asyncio.run(_run())
