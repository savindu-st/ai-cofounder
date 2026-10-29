"""Schema compliance metric.

The runner records every domain-agent invocation and whether its output
validated against the expected Pydantic contract.
"""

from typing import Iterable

from evaluation.metrics.base import MetricResult

TARGET = 0.95


def calculate(successful_invocations: Iterable[bool]) -> MetricResult:
    """Return the share of agent invocations with schema-valid outputs."""
    outcomes = [bool(value) for value in successful_invocations]
    total = len(outcomes)
    valid = sum(1 for value in outcomes if value)
    value = valid / total if total else 0.0
    passed = total > 0 and value > TARGET

    return MetricResult(
        name="Schema Compliance",
        value=round(value, 4),
        display=f"{value:.1%}",
        target=">95%",
        passed=passed,
        details={
            "valid_pydantic_contract_outputs": valid,
            "total_agent_invocations": total,
        },
    )
