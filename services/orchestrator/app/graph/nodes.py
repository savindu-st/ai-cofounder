"""LangGraph State Machine Node Functions.

Wraps in-process domain service interfaces as async LangGraph nodes, returning
delta updates to VentureState and emitting real-time execution events.
"""

from typing import Dict, Any

from shared.contracts.venture_state import VentureState
from shared.enums.workflow_status import WorkflowStage
from services.orchestrator.app.orchestration.event_bus import publish_event
from services.orchestrator.app.orchestration.failure_handler import (
    NodeExecutionError,
    run_node_operation,
)
from services.orchestrator.app.orchestration.human_review import pause_for_review
from services.orchestrator.app.orchestration.replanning import build_replan_updates
from services.orchestrator.app.state.state_manager import save_venture_state


async def _checkpoint(state: VentureState, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Persist a stage-boundary snapshot to the in-memory state cache."""
    try:
        await save_venture_state(state.model_copy(update=updates))
    except Exception:
        pass
    return updates


async def _invoke_domain(func, *args, node_name: str, state: VentureState, **kwargs):
    """Invoke a domain call with timeout, retry, and isolated failure reporting."""
    async def _on_retry(exc: BaseException, attempt: int, delay: float) -> None:
        await publish_event(
            venture_id=state.venture_id,
            stage=state.current_stage,
            event_type="WARNING",
            progress_pct=0,
            message=f"{node_name} transient failure (attempt {attempt}); retrying in {delay:.2f}s: {exc}",
            data={"node": node_name, "attempt": attempt},
        )

    try:
        return await run_node_operation(
            func,
            *args,
            node_name=node_name,
            on_retry=_on_retry,
            **kwargs,
        )
    except NodeExecutionError as exc:
        await publish_event(
            venture_id=state.venture_id,
            stage=WorkflowStage.FAILED,
            event_type="WARNING",
            progress_pct=0,
            message=f"{node_name} failed after retries: {exc.cause}",
            data={"node": node_name, "error": str(exc.cause)},
        )
        raise


async def idea_analysis_node(state: VentureState) -> Dict[str, Any]:
    """Node 1: Deconstructs raw founder input into assumptions, value prop, and target users."""
    await publish_event(
        venture_id=state.venture_id,
        stage=WorkflowStage.IDEA_ANALYSIS,
        event_type="STAGE_STARTED",
        progress_pct=15,
        message="Deconstructing founder assumptions, problem statement, and value proposition..."
    )

    from services.business_intelligence.app.interface import run_idea_analysis
    idea_output = await _invoke_domain(run_idea_analysis, state.founder_input, node_name="idea_analysis", state=state)

    await publish_event(
        venture_id=state.venture_id,
        stage=WorkflowStage.IDEA_ANALYSIS,
        event_type="STAGE_COMPLETED",
        progress_pct=25,
        message="Idea analysis completed. Moving to market research."
    )

    return await _checkpoint(state, {
        "current_stage": WorkflowStage.IDEA_ANALYSIS,
        "idea_analysis": idea_output,
    })


async def market_research_node(state: VentureState) -> Dict[str, Any]:
    """Node 2: Executes web search, competitor analysis, and market sizing."""
    await publish_event(
        venture_id=state.venture_id,
        stage=WorkflowStage.MARKET_RESEARCH,
        event_type="STAGE_STARTED",
        progress_pct=30,
        message="Researching competitor landscape, market sizing (TAM/SAM/SOM), and industry trends..."
    )

    from services.research.app.interface import run_market_research
    market_output = await _invoke_domain(
        run_market_research,
        state.idea_analysis,
        state.founder_input,
        state.critique_history,
        node_name="market_research",
        state=state,
    )

    await publish_event(
        venture_id=state.venture_id,
        stage=WorkflowStage.MARKET_RESEARCH,
        event_type="STAGE_COMPLETED",
        progress_pct=45,
        message="Market research and competitor landscape synthesized."
    )

    return await _checkpoint(state, {
        "current_stage": WorkflowStage.MARKET_RESEARCH,
        "market_research": market_output,
    })


async def critic_validation_node(state: VentureState) -> Dict[str, Any]:
    """Node 3: Evaluates market research claims against strict 3-point validation rubric."""
    await publish_event(
        venture_id=state.venture_id,
        stage=WorkflowStage.CRITIC_VALIDATION,
        event_type="STAGE_STARTED",
        progress_pct=50,
        message="Critic evaluating factual claims, citation sources, and confidence thresholds..."
    )

    from services.research.app.interface import run_critic_validation
    critic_output = await _invoke_domain(
        run_critic_validation,
        state.market_research,
        state.idea_analysis,
        node_name="critic_validation",
        state=state,
    )

    updated_history = list(state.critique_history) + [critic_output]

    await publish_event(
        venture_id=state.venture_id,
        stage=WorkflowStage.CRITIC_VALIDATION,
        event_type="STAGE_COMPLETED",
        progress_pct=60,
        message=f"Critic validation status: {critic_output.status}. Confidence: {critic_output.confidence_score:.2f}."
    )

    return await _checkpoint(state, {
        "current_stage": WorkflowStage.CRITIC_VALIDATION,
        "market_validation": critic_output,
        "critique_history": updated_history,
    })


async def business_model_node(state: VentureState) -> Dict[str, Any]:
    """Node 4: Synthesizes 9-block Osterwalder Business Model Canvas via RAG."""
    await publish_event(
        venture_id=state.venture_id,
        stage=WorkflowStage.BUSINESS_MODEL,
        event_type="STAGE_STARTED",
        progress_pct=65,
        message="Retrieving startup frameworks and synthesizing 9-block Business Model Canvas..."
    )

    from services.business_intelligence.app.interface import run_business_model
    bm_output = await _invoke_domain(
        run_business_model,
        state.idea_analysis,
        state.market_research,
        node_name="business_model",
        state=state,
    )

    await publish_event(
        venture_id=state.venture_id,
        stage=WorkflowStage.BUSINESS_MODEL,
        event_type="STAGE_COMPLETED",
        progress_pct=75,
        message="Business Model Canvas synthesized successfully."
    )

    return await _checkpoint(state, {
        "current_stage": WorkflowStage.BUSINESS_MODEL,
        "business_model": bm_output,
    })


async def revenue_estimation_node(state: VentureState) -> Dict[str, Any]:
    """Node 5: Computes deterministic 12-36 month projections and scenario models."""
    await publish_event(
        venture_id=state.venture_id,
        stage=WorkflowStage.REVENUE_ESTIMATION,
        event_type="STAGE_STARTED",
        progress_pct=80,
        message="Running deterministic financial engine across Conservative, Moderate, and Optimistic scenarios..."
    )

    from services.finance.app.interface import run_revenue_estimation
    critique_notes = None
    if state.revenue_estimation and state.revenue_estimation.invariant_violations:
        critique_notes = "; ".join(state.revenue_estimation.invariant_violations)
    rev_output = await _invoke_domain(
        run_revenue_estimation,
        state.idea_analysis,
        state.market_research,
        state.business_model,
        founder=state.founder_input,
        critique_notes=critique_notes,
        retune_round=state.finance_retune_count,
        node_name="revenue_estimation",
        state=state,
    )

    await publish_event(
        venture_id=state.venture_id,
        stage=WorkflowStage.REVENUE_ESTIMATION,
        event_type="STAGE_COMPLETED",
        progress_pct=88,
        message="Financial projections and unit economics verified."
    )

    return await _checkpoint(state, {
        "current_stage": WorkflowStage.REVENUE_ESTIMATION,
        "revenue_estimation": rev_output,
    })


async def marketing_plan_node(state: VentureState) -> Dict[str, Any]:
    """Node 6: Formulates Bullseye channel prioritization, budget allocation, and 90-day plan."""
    await publish_event(
        venture_id=state.venture_id,
        stage=WorkflowStage.MARKETING,
        event_type="STAGE_STARTED",
        progress_pct=90,
        message="Formulating Bullseye traction channels, unit economics budget, and 12-week sprint plan..."
    )

    from services.marketing_output.app.interface import run_marketing_plan
    mktg_output = await _invoke_domain(
        run_marketing_plan,
        state.idea_analysis,
        state.market_research,
        state.business_model,
        state.revenue_estimation,
        state.founder_input,
        node_name="marketing_plan",
        state=state,
    )

    await publish_event(
        venture_id=state.venture_id,
        stage=WorkflowStage.MARKETING,
        event_type="STAGE_COMPLETED",
        progress_pct=95,
        message="Marketing and go-to-market plan formulated."
    )

    return await _checkpoint(state, {
        "current_stage": WorkflowStage.MARKETING,
        "marketing_plan": mktg_output,
    })


async def roadmap_synthesis_node(state: VentureState) -> Dict[str, Any]:
    """Node 7 (Terminal): Synthesizes unified executive StartupRoadmap from all stage outputs."""
    await publish_event(
        venture_id=state.venture_id,
        stage=WorkflowStage.ROADMAP_COMPILATION,
        event_type="STAGE_STARTED",
        progress_pct=98,
        message="Synthesizing executive Startup Roadmap and milestone matrix..."
    )

    from services.marketing_output.app.interface import run_roadmap_synthesis
    roadmap_output = await _invoke_domain(run_roadmap_synthesis, state, node_name="roadmap_synthesis", state=state)

    await publish_event(
        venture_id=state.venture_id,
        stage=WorkflowStage.COMPLETED,
        event_type="ROADMAP_READY",
        progress_pct=100,
        message="Startup Roadmap fully compiled and ready.",
        data={"overall_confidence": roadmap_output.overall_confidence_score}
    )

    return await _checkpoint(state, {
        "current_stage": WorkflowStage.COMPLETED,
        "final_roadmap": roadmap_output,
    })


async def replanning_node(state: VentureState) -> Dict[str, Any]:
    """Determine the smallest repair stage and record anti-oscillation context."""
    decision = build_replan_updates(state)

    await publish_event(
        venture_id=state.venture_id,
        stage=WorkflowStage.REPLANNING,
        event_type="REPLAN_TRIGGERED",
        progress_pct=55,
        message=decision.reason,
        data={
            "target": decision.target,
            "replan_count": state.replan_count,
            "market_replan_count": state.market_replan_count,
            "finance_retune_count": state.finance_retune_count,
            "oscillation_count": decision.oscillation_count,
        },
    )
    if decision.is_oscillating:
        await publish_event(
            venture_id=state.venture_id,
            stage=WorkflowStage.REPLANNING,
            event_type="WARNING",
            progress_pct=55,
            message=(
                "Repeated critique detected; escalating the repair target to avoid "
                "an unproductive oscillation loop."
            ),
            data={"target": decision.target, "oscillation_count": decision.oscillation_count},
        )

    return await _checkpoint(state, decision.updates)


async def human_review_node(state: VentureState) -> Dict[str, Any]:
    """Pause Node: Interrupted by LangGraph for founder review when threshold exceeded."""
    reason = "Human-in-the-Loop review required: automated re-planning threshold exceeded."
    await publish_event(
        venture_id=state.venture_id,
        stage="HUMAN_REVIEW",
        event_type="HITL_REQUIRED",
        progress_pct=min(100, state.replan_count * 10),
        message=reason,
        data={"replan_count": state.replan_count, "warnings": state.warnings[-5:]},
    )

    return await _checkpoint(state, pause_for_review(reason))
