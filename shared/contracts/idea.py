from typing import List, Optional
from pydantic import Field
from shared.contracts.base import BaseContract

class FounderInput(BaseContract):
    startup_idea: str
    target_market: str
    target_geography: str = "Global"
    budget: float = 0.0
    timeline_months: int = 3
    goals: str = ""
    constraints: List[str] = Field(default_factory=list)
    skills_resources: Optional[str] = None

class IdeaAnalysisOutput(BaseContract):
    problem_statement: str
    target_users: List[str]
    refined_value_proposition: str
    key_assumptions: List[str]
    red_flags: List[str] = Field(default_factory=list)
    clarity_score: float = Field(ge=0.0, le=1.0)
    feasibility_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
