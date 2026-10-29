from typing import List, Optional
from pydantic import Field
from shared.contracts.base import BaseContract
from shared.contracts.idea import IdeaAnalysisOutput, FounderInput
from shared.contracts.market import MarketResearchOutput
from shared.contracts.business_model import BusinessModelOutput
from shared.contracts.revenue import RevenueEstimationOutput
from shared.contracts.marketing import MarketingPlanOutput

class ExecutionPhase(BaseContract):
    """A phased milestone block in the final startup execution roadmap."""
    phase_number: int = Field(ge=1)
    name: str
    duration_weeks: int = Field(default=4, ge=1)
    focus: str
    key_milestones: List[str] = Field(default_factory=list)
    success_metrics: List[str] = Field(default_factory=list)

class VentureRisk(BaseContract):
    """A cross-functional venture risk with an explicit mitigation."""
    category: str
    risk: str
    likelihood: str = "MEDIUM"
    impact: str = "HIGH"
    mitigation: str

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
    execution_phases: List[ExecutionPhase] = Field(default_factory=list)
    top_risks: List[VentureRisk] = Field(default_factory=list)
