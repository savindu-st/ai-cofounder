"""End-to-end latency metric."""

from typing import Iterable

from evaluation.metrics.base import MetricResult

TARGET_SECONDS = 8 * 60


def calculate(durations_seconds: Iterable[float]) -> MetricResult:
    """Return worst-case latency; every benchmark run must stay below the target."""
    durations = [max(0.0, float(value)) for value in durations_seconds]
    worst_case = max(durations) if durations else 0.0
    average = sum(durations) / len(durations) if durations else 0.0
    passed = bool(durations) and worst_case < TARGET_SECONDS

    return MetricResult(
        name="End-to-End Latency",
        value=round(worst_case, 4),
        display=f"{worst_case:.2f}s",
        target=f"<{TARGET_SECONDS}s",
        passed=passed,
        details={
            "worst_case_seconds": round(worst_case, 4),
            "average_seconds": round(average, 4),
            "samples": [round(value, 4) for value in durations],
        },
    )
