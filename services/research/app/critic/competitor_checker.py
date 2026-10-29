"""Competitor Depth and Real-Business Validation Checker.

Evaluates competitor landscape quality: minimum competitor count, naming uniqueness,
feature/pricing depth, and structural weaknesses.
"""

from dataclasses import dataclass, field
from typing import List, Set
from shared.contracts.market import Competitor


@dataclass
class CompetitorDepthReport:
    """Audit report for competitor landscape granularity."""
    competitor_count: int
    depth_score: float
    has_pricing_coverage: bool
    unique_names: int
    warnings: List[str] = field(default_factory=list)
    is_acceptable: bool = False


class CompetitorChecker:
    """Evaluates the structural depth and realism of identified competitors."""

    MIN_COMPETITORS = 2
    TARGET_COMPETITORS = 3

    def evaluate(self, competitors: List[Competitor]) -> CompetitorDepthReport:
        """Evaluates competitor array against enterprise diligence standards."""
        if not competitors:
            return CompetitorDepthReport(
                competitor_count=0,
                depth_score=0.0,
                has_pricing_coverage=False,
                unique_names=0,
                warnings=["Competitor landscape is completely empty."],
                is_acceptable=False
            )

        warnings: List[str] = []
        count = len(competitors)
        names_seen: Set[str] = set()
        total_points = 0.0
        max_possible_points = float(count) * 4.0  # 4 criteria per competitor
        pricing_count = 0

        for comp in competitors:
            clean_name = comp.name.strip().lower()
            if clean_name in names_seen:
                warnings.append(f"Duplicate competitor identified: '{comp.name}'")
            names_seen.add(clean_name)

            # 1. Description depth (min 15 chars)
            if comp.description and len(comp.description.strip()) >= 15:
                total_points += 1.0
            else:
                warnings.append(f"Competitor '{comp.name}' has superficial or missing description.")

            # 2. Strengths and Weaknesses populated
            has_strengths = bool(comp.strengths and len(comp.strengths) >= 1)
            has_weaknesses = bool(comp.weaknesses and len(comp.weaknesses) >= 1)
            if has_strengths and has_weaknesses:
                total_points += 1.0
            elif has_strengths or has_weaknesses:
                total_points += 0.5
                warnings.append(f"Competitor '{comp.name}' is missing either strengths or weaknesses.")
            else:
                warnings.append(f"Competitor '{comp.name}' has zero strengths and weaknesses listed.")

            # 3. Pricing Model present
            if comp.pricing_model and len(comp.pricing_model.strip()) > 3:
                total_points += 1.0
                pricing_count += 1
            else:
                warnings.append(f"Competitor '{comp.name}' lacks pricing model or tier estimate.")

            # 4. Website or reference URL
            if comp.website_url and ("http://" in comp.website_url or "https://" in comp.website_url):
                total_points += 1.0
            else:
                total_points += 0.5  # minor penalty

        # Count penalty if below minimum
        if count < self.MIN_COMPETITORS:
            warnings.append(f"Too few competitors ({count}): minimum required is {self.MIN_COMPETITORS}.")

        raw_score = total_points / max_possible_points if max_possible_points > 0 else 0.0

        # Scale by count adequacy
        count_factor = min(1.0, count / float(self.TARGET_COMPETITORS))
        final_depth_score = round(raw_score * count_factor, 2)

        has_pricing_coverage = (pricing_count >= (count // 2))
        is_acceptable = (count >= self.MIN_COMPETITORS) and (final_depth_score >= 0.65) and (len(names_seen) == count)

        return CompetitorDepthReport(
            competitor_count=count,
            depth_score=final_depth_score,
            has_pricing_coverage=has_pricing_coverage,
            unique_names=len(names_seen),
            warnings=warnings,
            is_acceptable=is_acceptable
        )
