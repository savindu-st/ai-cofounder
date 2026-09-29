"""Graph Edge Definitions and Route Mapping Constants."""

# Route mapping dictionaries for LangGraph conditional edges
CRITIC_ROUTES = {
    "business_model": "business_model",
    "market_research": "market_research",
    "idea_analysis": "idea_analysis",
    "human_review": "human_review"
}

REVENUE_ROUTES = {
    "marketing_plan": "marketing_plan",
    "revenue_estimation": "revenue_estimation",
    "market_research": "market_research",
    "human_review": "human_review"
}

HUMAN_REVIEW_ROUTES = {
    "business_model": "business_model",
    "idea_analysis": "idea_analysis",
    "end": "__end__"
}
