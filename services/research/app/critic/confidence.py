"""Composite Confidence Scoring Engine.

Combines four orthogonal validation signals into a calibrated confidence score:
1. Citation quality and domain diversity (30% weight)
2. Competitor landscape depth and pricing coverage (25% weight)
3. Factual claim grounding ratio (25% weight)
4. Market sizing invariant validity (20% weight)
"""

from typing import Dict, Any
from services.research.app.critic.citation_validator import CitationReport
from services.research.app.critic.competitor_checker import CompetitorDepthReport
from services.research.app.critic.evidence_validator import EvidenceReport


class CompositeConfidenceScorer:
    """Computes a multi-dimensional confidence score for market research validation."""

    WEIGHT_CITATION = 0.30
    WEIGHT_COMPETITOR = 0.25
    WEIGHT_EVIDENCE = 0.25
    WEIGHT_SIZING = 0.20

    def compute_score(
        self,
        citation_report: CitationReport,
        competitor_report: CompetitorDepthReport,
        evidence_report: EvidenceReport,
        sizing_valid: bool,
        agent_self_score: float = 0.85
    ) -> Dict[str, Any]:
        """Calculates calibrated confidence score and returns detailed component breakdown."""
        # 1. Citation Subscore
        if citation_report.total_urls == 0:
            citation_subscore = 0.0
        else:
            # Reward valid URLs and domain diversity, penalize placeholders
            valid_ratio = min(1.0, float(citation_report.valid_urls) / 2.0)
            diversity_bonus = 0.2 if citation_report.unique_domains >= 2 else 0.0
            placeholder_penalty = 0.5 if citation_report.placeholder_urls > 0 else 0.0
            citation_subscore = max(0.0, min(1.0, (valid_ratio * 0.8 + diversity_bonus) - placeholder_penalty))

        # 2. Competitor Subscore
        competitor_subscore = max(0.0, min(1.0, competitor_report.depth_score))

        # 3. Evidence Subscore
        evidence_subscore = max(0.0, min(1.0, evidence_report.grounding_score))

        # 4. Sizing Subscore
        sizing_subscore = 1.0 if sizing_valid else 0.0

        # Weighted aggregate
        composite = (
            self.WEIGHT_CITATION * citation_subscore
            + self.WEIGHT_COMPETITOR * competitor_subscore
            + self.WEIGHT_EVIDENCE * evidence_subscore
            + self.WEIGHT_SIZING * sizing_subscore
        )

        # Blend slightly with agent self-score (85% objective rubric, 15% model self-assessment)
        final_score = (0.85 * composite) + (0.15 * min(1.0, max(0.0, agent_self_score)))
        final_score = round(max(0.0, min(1.0, final_score)), 2)

        return {
            "confidence_score": final_score,
            "components": {
                "citation_subscore": round(citation_subscore, 2),
                "competitor_subscore": round(competitor_subscore, 2),
                "evidence_subscore": round(evidence_subscore, 2),
                "sizing_subscore": round(sizing_subscore, 2),
                "agent_self_score": round(agent_self_score, 2)
            }
        }
