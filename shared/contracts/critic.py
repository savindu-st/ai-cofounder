from typing import List
from pydantic import Field
from shared.contracts.base import BaseContract
from shared.enums.confidence_level import ValidationStatus

class CriticValidationOutput(BaseContract):
    status: ValidationStatus
    confidence_score: float = Field(ge=0.0, le=1.0)
    unsupported_claims: List[str] = Field(default_factory=list)
    verified_sources_count: int = 0
    feedback_notes: str = ""
    requires_pivot: bool = False
    suggested_alternatives: List[str] = Field(default_factory=list)
