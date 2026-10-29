"""Token usage and dollar-cost tracking metric."""

from dataclasses import dataclass
from typing import Iterable, Optional

from evaluation.metrics.base import MetricResult


@dataclass(frozen=True)
class TokenUsage:
    """Token counts for one agent invocation."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = "default"


@dataclass(frozen=True)
class ModelPricing:
    """USD prices per one million tokens."""

    prompt_per_million: float = 0.15
    completion_per_million: float = 0.60


DEFAULT_PRICING = ModelPricing()


def calculate(
    usages: Iterable[TokenUsage],
    pricing: Optional[ModelPricing] = None,
) -> MetricResult:
    """Return aggregate token usage and estimated cost."""
    rates = pricing or DEFAULT_PRICING
    records = list(usages)
    prompt_tokens = sum(max(0, record.prompt_tokens) for record in records)
    completion_tokens = sum(max(0, record.completion_tokens) for record in records)
    cost = (
        prompt_tokens * rates.prompt_per_million
        + completion_tokens * rates.completion_per_million
    ) / 1_000_000

    display = f"${cost:.6f}" if cost < 0.01 else f"${cost:.4f}"

    return MetricResult(
        name="Cost per Venture",
        value=round(cost, 6),
        display=display,
        target="track",
        passed=None,
        details={
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "estimated_cost_usd": round(cost, 6),
            "prompt_price_per_million": rates.prompt_per_million,
            "completion_price_per_million": rates.completion_per_million,
            "invocations": len(records),
            "source": "estimated_from_agent_payload_sizes",
        },
    )
