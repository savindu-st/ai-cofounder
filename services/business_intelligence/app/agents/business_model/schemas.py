"""Pydantic schemas for RAG-powered Business Model Canvas synthesis."""

from typing import List
from pydantic import BaseModel, Field


class CanvasSynthesis(BaseModel):
    """Internal model for structured 9-block Osterwalder canvas synthesis."""
    key_partners: List[str] = Field(description="2-4 key suppliers, alliance partners, or platform dependencies")
    key_activities: List[str] = Field(description="2-4 core operational actions required to deliver value")
    key_resources: List[str] = Field(description="2-4 physical, intellectual, human, or capital assets")
    value_propositions: List[str] = Field(description="2-4 core value bundles solving customer problems")
    customer_relationships: List[str] = Field(description="2-4 engagement/support models (e.g. self-service, PLG)")
    channels: List[str] = Field(description="2-4 marketing, sales, and distribution pathways")
    customer_segments: List[str] = Field(description="2-4 distinct user or buyer personas served")
    cost_structure: List[str] = Field(description="2-4 primary operational cost drivers and overhead items")
    revenue_streams: List[str] = Field(description="2-4 monetization mechanisms (e.g. subscription tiers, usage fees)")
    key_risks: List[str] = Field(default_factory=list, description="Top 2-3 strategic or operational risks")
    mitigations: List[str] = Field(default_factory=list, description="Actionable countermeasures for the key risks")
    confidence_score: float = Field(default=0.85, ge=0.0, le=1.0, description="Overall confidence score in model viability")
