"""Pydantic Schemas for Market Research Agent Output and Intermediate Representations."""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class CompetitorSchema(BaseModel):
    """Schema for individual competitor extracted during research."""
    name: str = Field(description="Name of the competing company or platform")
    description: str = Field(description="Overview of their product, positioning, and core target audience")
    strengths: List[str] = Field(default_factory=list, description="Key competitive advantages and moat")
    weaknesses: List[str] = Field(default_factory=list, description="Known customer pain points or limitations")
    pricing_model: Optional[str] = Field(default=None, description="Reported or estimated pricing tiers (e.g. $49/mo, $500/seat)")
    website_url: Optional[str] = Field(default=None, description="Direct URL to company website or pricing page")
    source_url: Optional[str] = Field(default=None, description="External citation where this competitor was identified")


class MarketSizingSchema(BaseModel):
    """Structured market sizing estimation."""
    tam: float = Field(ge=0.0, description="Total Addressable Market in USD")
    sam: float = Field(ge=0.0, description="Serviceable Available Market in USD")
    som: float = Field(ge=0.0, description="Serviceable Obtainable Market (Year 1-2 projection) in USD")
    cagr_pct: Optional[float] = Field(default=None, description="Projected annual market growth percentage (CAGR)")
    methodology: str = Field(default="triangulated", description="Calculation methodology: top-down, bottom-up, or triangulated")
    source_citations: List[str] = Field(default_factory=list, description="URLs supporting the market sizing calculation")


class MarketResearchSynthesis(BaseModel):
    """Full structured synthesis produced by Market Research Agent LLM."""
    competitor_landscape: List[CompetitorSchema] = Field(
        min_length=2,
        description="3-5 direct or indirect competitors with full profile depth"
    )
    customer_personas: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Target customer personas with role, primary pain point, and willingness to pay"
    )
    market_trends: List[str] = Field(
        default_factory=list,
        description="Macro and micro industry trends driving market adoption"
    )
    entry_barriers: List[str] = Field(
        default_factory=list,
        description="Key regulatory, technical, or distribution hurdles"
    )
    market_sizing: MarketSizingSchema = Field(
        description="Calculated TAM/SAM/SOM estimates backed by methodology"
    )
    supporting_evidence: List[str] = Field(
        default_factory=list,
        description="Factual claims paired with explicit source citations"
    )
    source_urls: List[str] = Field(
        min_length=2,
        description="Verified external URLs consulted during synthesis"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        default=0.85,
        description="Self-assessed confidence score based on data availability and depth"
    )
