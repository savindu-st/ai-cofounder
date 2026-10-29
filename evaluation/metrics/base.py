"""Shared evaluation metric result type."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class MetricResult:
    """Normalized result returned by every evaluation metric."""

    name: str
    value: float
    display: str
    target: str
    passed: Optional[bool]
    details: Dict[str, Any] = field(default_factory=dict)
