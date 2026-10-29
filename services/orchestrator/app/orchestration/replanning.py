"""Re-planning engine.

Builds critique context, detects repeated/oscillating feedback, chooses a
targeted repair stage, and produces immutable state deltas for the graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional

from shared.contracts.critic import CriticValidationOutput
from shared.contracts.venture_state import VentureState
from shared.enums.confidence_level import ValidationStatus
from shared.enums.workflow_status import WorkflowStage

REPLAN_IDEA = "idea_analysis"
REPLAN_MARKET = "market_research"
REPLAN_FINANCE = "revenue_estimation"
REPLAN_HUMAN = "human_review"

MAX_TOTAL_REPLANS = 5
MAX_FINANCE_RETUNES = 2


@dataclass(frozen=True)
class ReplanDecision:
    target: str
    reason: str
    updates: dict[str, Any] = field(default_factory=dict)
    oscillation_count: int = 0

    @property
    def is_oscillating(self) -> bool:
        return self.oscillation_count >= 2


def _normalize_issue(issue: str) -> str:
    return " ".join(issue.strip().lower().split())[:160]


def critique_signature(critic: CriticValidationOutput) -> str:
    """Stable signature used to spot repeated, non-improving critique cycles."""
    status = critic.status.value if hasattr(critic.status, "value") else str(critic.status)
    issues = sorted({_normalize_issue(claim) for claim in critic.unsupported_claims if claim.strip()})
    if not issues:
        issues = [_normalize_issue(critic.feedback_notes or "unspecified validation failure")]
    return f"{status}|" + "|".join(issues[:8])


def consecutive_oscillations(history: Iterable[CriticValidationOutput]) -> int:
    """Count trailing critique entries with the identical failure signature."""
    signatures = [critique_signature(item) for item in history]
    if not signatures:
        return 0
    latest = signatures[-1]
    count = 0
    for signature in reversed(signatures):
        if signature != latest:
            break
        count += 1
    return count


def build_critique_context(
    history: Iterable[CriticValidationOutput],
    max_chars: int = 2000,
) -> str:
    """Construct compact critique context for downstream research prompts."""
    items = list(history)
    if not items:
        return ""

    latest = items[-1]
    status = latest.status.value if hasattr(latest.status, "value") else str(latest.status)
    issues = latest.unsupported_claims[:6]
    lines = [
        f"Latest critic status: {status} (confidence {latest.confidence_score:.2f}).",
        f"Validator feedback: {latest.feedback_notes or 'No additional notes.'}",
    ]
    if issues:
        lines.append("Recurring issues to resolve:")
        lines.extend(f"- {issue}" for issue in issues)
    if len(items) > 1:
        lines.append(f"Validation attempts so far: {len(items)}.")
    context = "\n".join(lines)
    return context[:max_chars]


def _latest_critique(state: VentureState) -> Optional[CriticValidationOutput]:
    if state.critique_history:
        return state.critique_history[-1]
    return state.market_validation


def _append_warning(warnings: List[str], warning: str) -> None:
    if warning not in warnings:
        warnings.append(warning)


def determine_replan_target(state: VentureState) -> str:
    """Choose the smallest upstream stage likely to fix the current failure."""
    critique = _latest_critique(state)
    if critique is not None and critique.status != ValidationStatus.VALID:
        if critique.requires_pivot or critique.status == ValidationStatus.REANALYSIS_REQUIRED:
            return REPLAN_IDEA
        return REPLAN_MARKET

    revenue = state.revenue_estimation
    if revenue is not None:
        finance_invalid = (
            not revenue.tam_sam_som_valid
            or bool(revenue.invariant_violations)
        )
        if finance_invalid:
            if state.finance_retune_count < MAX_FINANCE_RETUNES:
                return REPLAN_FINANCE
            return REPLAN_MARKET

    return state.replan_target or REPLAN_MARKET


def _replan_reason(state: VentureState, target: str) -> str:
    critique = _latest_critique(state)
    if critique is not None and critique.status != ValidationStatus.VALID:
        detail = critique.feedback_notes or ", ".join(critique.unsupported_claims[:3])
        return f"{target} required after {critique.status.value}: {detail}"
    if state.revenue_estimation is not None and state.revenue_estimation.invariant_violations:
        detail = "; ".join(state.revenue_estimation.invariant_violations[:3])
        return f"{target} required after financial invariant failure: {detail}"
    return f"{target} selected for targeted re-planning."


def build_replan_updates(
    state: VentureState,
    target: Optional[str] = None,
) -> ReplanDecision:
    """Compute the next repair target, counter increments, and warnings."""
    selected = target or determine_replan_target(state)
    warnings = list(state.warnings)
    reason = _replan_reason(state, selected)
    oscillation_count = consecutive_oscillations(state.critique_history)

    updates: dict[str, Any] = {
        "current_stage": WorkflowStage.REPLANNING,
        "replan_target": selected,
        "human_review_required": False,
    }

    if selected == REPLAN_IDEA:
        updates["replan_count"] = state.replan_count + 1
    elif selected == REPLAN_MARKET:
        updates["replan_count"] = state.replan_count + 1
        updates["market_replan_count"] = state.market_replan_count + 1
    elif selected == REPLAN_FINANCE:
        updates["finance_retune_count"] = state.finance_retune_count + 1

    _append_warning(warnings, reason)
    if oscillation_count >= 2:
        _append_warning(
            warnings,
            f"Anti-oscillation warning: the same critic failure repeated "
            f"{oscillation_count} times; targeted {selected} retry is in progress.",
        )

    updates["warnings"] = warnings
    return ReplanDecision(
        target=selected,
        reason=reason,
        updates=updates,
        oscillation_count=oscillation_count,
    )


def should_pause_for_human(state: VentureState) -> bool:
    """Return True when the automated replan budget is exhausted."""
    return state.replan_count >= MAX_TOTAL_REPLANS


def needs_financial_replan(state: VentureState) -> bool:
    revenue = state.revenue_estimation
    if revenue is None:
        return False
    return (not revenue.tam_sam_som_valid) or bool(revenue.invariant_violations)
