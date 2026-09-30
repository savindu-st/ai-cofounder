"""Pydantic schemas for Idea Analysis Agent."""

from typing import List, Optional
from pydantic import BaseModel, Field


class PersonaSketch(BaseModel):
    """Early target customer persona profile."""
    name: str = Field(description="Name or title of persona (e.g. SRE Lead)")
    description: str = Field(description="Brief demographic/role description")
    pain_points: List[str] = Field(default_factory=list, description="Top acute frustrations")
    willingness_to_pay: str = Field(default="Medium", description="High, Medium, or Low")


class IdeaDecomposition(BaseModel):
    """Structured decomposition produced by the Idea Analysis Agent."""
    problem_statement: str = Field(description="Crisp statement of the root problem being solved")
    target_users: List[str] = Field(description="Identified user groups or buyer segments")
    refined_value_proposition: str = Field(description="Clear UVP emphasizing customer benefits and differentiation")
    key_assumptions: List[str] = Field(description="Critical testable hypotheses that must hold true")
    unfair_advantages: List[str] = Field(default_factory=list, description="Defensible structural moats")
    audience_personas: List[PersonaSketch] = Field(default_factory=list, description="Persona profiles")
    red_flags: List[str] = Field(default_factory=list, description="Potential unviable risks or fatal flaws")
    clarity_score: float = Field(ge=0.0, le=1.0, description="Clarity and specificity score")
    feasibility_score: float = Field(ge=0.0, le=1.0, description="Technical and operational feasibility score")
