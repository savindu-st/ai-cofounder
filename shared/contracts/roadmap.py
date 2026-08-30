from typing import List, Optional
from pydantic import Field
from shared.contracts.base import BaseContract
from shared.contracts.idea import IdeaAnalysisOutput, FounderInput
from shared.contracts.market import MarketResearchOutput
from shared.contracts.business_model import BusinessModelOutput
from shared.contracts.revenue import RevenueEstimationOutput
from shared.contracts.marketing import MarketingPlanOutput

class StartupRoadmap(BaseContract):
    venture_id: str
    venture_name: str
    founder_input: FounderInput
    idea_analysis: IdeaAnalysisOutput
    market_research: MarketResearchOutput
    business_model: BusinessModelOutput
    revenue_estimation: RevenueEstimationOutput
    marketing_plan: MarketingPlanOutput
    overall_confidence_score: float
    executive_summary: str
    disclaimer: str = "This document is an AI-generated decision-support roadmap and does not constitute formal legal, tax, or investment advice."
