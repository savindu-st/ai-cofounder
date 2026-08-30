from typing import List, Dict
from pydantic import Field
from shared.contracts.base import BaseContract

class BusinessModelCanvas(BaseContract):
    key_partners: List[str] = Field(default_factory=list)
    key_activities: List[str] = Field(default_factory=list)
    key_resources: List[str] = Field(default_factory=list)
    value_propositions: List[str] = Field(default_factory=list)
    customer_relationships: List[str] = Field(default_factory=list)
    channels: List[str] = Field(default_factory=list)
    customer_segments: List[str] = Field(default_factory=list)
    cost_structure: List[str] = Field(default_factory=list)
    revenue_streams: List[str] = Field(default_factory=list)

class BusinessModelOutput(BaseContract):
    framework_used: str = "Business Model Canvas"
    canvas: BusinessModelCanvas
    key_risks: List[str] = Field(default_factory=list)
    mitigations: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
