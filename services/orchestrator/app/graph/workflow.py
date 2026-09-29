"""LangGraph StateGraph Core Definition.

Constructs, wires, and compiles the autonomous 7-node multi-agent venture creation
workflow with conditional self-healing edges and checkpointer persistence.
"""

from typing import Optional, Any
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from shared.contracts.venture_state import VentureState
from services.orchestrator.app.graph.nodes import (
    idea_analysis_node,
    market_research_node,
    critic_validation_node,
    business_model_node,
    revenue_estimation_node,
    marketing_plan_node,
    roadmap_synthesis_node,
    human_review_node
)
from services.orchestrator.app.graph.routing import (
    route_after_critic,
    route_after_revenue,
    route_after_human_review
)
from services.orchestrator.app.graph.edges import (
    CRITIC_ROUTES,
    REVENUE_ROUTES,
    HUMAN_REVIEW_ROUTES
)


def build_venture_workflow(
    checkpointer: Optional[Any] = None,
    enable_hitl_interrupt: bool = True
):
    """Builds and compiles the complete LangGraph venture creation workflow.
    
    Args:
        checkpointer: Optional LangGraph checkpointer (defaults to MemorySaver).
        enable_hitl_interrupt: If True, suspends execution when entering human_review.
        
    Returns:
        CompiledGraph executable for invoke/ainvoke with thread config.
    """
    builder = StateGraph(VentureState)

    # 1. Register domain node wrappers
    builder.add_node("idea_analysis", idea_analysis_node)
    builder.add_node("market_research", market_research_node)
    builder.add_node("critic_validation", critic_validation_node)
    builder.add_node("business_model", business_model_node)
    builder.add_node("revenue_estimation", revenue_estimation_node)
    builder.add_node("marketing_plan", marketing_plan_node)
    builder.add_node("roadmap_synthesis", roadmap_synthesis_node)
    builder.add_node("human_review", human_review_node)

    # 2. Register deterministic linear transitions
    builder.add_edge(START, "idea_analysis")
    builder.add_edge("idea_analysis", "market_research")
    builder.add_edge("market_research", "critic_validation")
    builder.add_edge("business_model", "revenue_estimation")
    builder.add_edge("marketing_plan", "roadmap_synthesis")
    builder.add_edge("roadmap_synthesis", END)

    # 3. Register conditional branching edges
    builder.add_conditional_edges(
        "critic_validation",
        route_after_critic,
        CRITIC_ROUTES
    )

    builder.add_conditional_edges(
        "revenue_estimation",
        route_after_revenue,
        REVENUE_ROUTES
    )

    builder.add_conditional_edges(
        "human_review",
        route_after_human_review,
        HUMAN_REVIEW_ROUTES
    )

    # 4. Attach checkpointer
    if checkpointer is None:
        checkpointer = MemorySaver()

    interrupts = ["human_review"] if enable_hitl_interrupt else []

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupts
    )
