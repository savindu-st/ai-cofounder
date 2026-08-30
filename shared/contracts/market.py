from typing import List, Optional, Dict
from pydantic import Field
from shared.contracts.base import BaseContract

class Competitor(BaseContract):
    name: str
    description: str
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    pricing_model: Optional[str] = None
    website_url: Optional[str] = None

class MarketResearchOutput(BaseContract):
    competitor_landscape: List[Competitor]
    customer_personas: List[Dict[str, str]]
    market_trends: List[str]
    entry_barriers: List[str]
    tam_estimate: Optional[float] = None
    sam_estimate: Optional[float] = None
    som_estimate: Optional[float] = None
    supporting_evidence: List[str] = Field(default_factory=list)
    source_urls: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
