"""Workflow convergence metric."""

from typing import Iterable

from evaluation.metrics.base import MetricResult

TARGET = 0.90


def calculate(completed_runs: Iterable[bool]) -> MetricResult:
    """Return the share of started ventures that reached COMPLETED."""
    outcomes = [bool(value) for value in completed_runs]
    total = len(outcomes)
    completed = sum(1 for value in outcomes if value)
    value = completed / total if total else 0.0
    passed = total > 0 and value >= TARGET

    return MetricResult(
        name="Workflow Completion",
        value=round(value, 4),
        display=f"{value:.1%}",
        target=">=90%",
        passed=passed,
        details={
            "ventures_reaching_completed": completed,
            "total_ventures_started": total,
        },
    )
