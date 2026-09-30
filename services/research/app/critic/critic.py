"""Strict 3-Point Critic Rubric Engine.

Evaluates MarketResearchOutput against enterprise due diligence standards:
1. Confidence score >= 0.70
2. Verified sources count >= 2
3. Zero unverified / unsupported claims (len(unsupported_claims) == 0)
Emits CriticValidationOutput with calibrated status and actionable feedback.
"""

import logging
from typing import List, Optional

from shared.contracts.idea import IdeaAnalysisOutput
from shared.contracts.market import MarketResearchOutput
from shared.contracts.critic import CriticValidationOutput
from shared.enums.confidence_level import ValidationStatus

from services.research.app.critic.citation_validator import CitationValidator, CitationReport
from services.research.app.critic.competitor_checker import CompetitorChecker, CompetitorDepthReport
from services.research.app.critic.evidence_validator import EvidenceValidator, EvidenceReport
from services.research.app.critic.confidence import CompositeConfidenceScorer
from services.research.app.agents.market_research.market_sizing import MarketSizingEngine

logger = logging.getLogger(__name__)


class CriticEngine:
    """Rigorous due diligence critic enforcing the 3-point validation rubric."""

    CONFIDENCE_PASS_THRESHOLD = 0.70
    MIN_VERIFIED_SOURCES = 2

    def __init__(
        self,
        citation_validator: Optional[CitationValidator] = None,
        competitor_checker: Optional[CompetitorChecker] = None,
        evidence_validator: Optional[EvidenceValidator] = None,
        confidence_scorer: Optional[CompositeConfidenceScorer] = None
    ):
        self.citation_validator = citation_validator or CitationValidator()
        self.competitor_checker = competitor_checker or CompetitorChecker()
        self.evidence_validator = evidence_validator or EvidenceValidator()
        self.confidence_scorer = confidence_scorer or CompositeConfidenceScorer()

    def evaluate(
        self,
        market: MarketResearchOutput,
        idea: Optional[IdeaAnalysisOutput] = None
    ) -> CriticValidationOutput:
        """Applies the strict 3-point rubric and determines validation status."""
        unsupported_claims: List[str] = []
        feedback_items: List[str] = []
        suggested_alternatives: List[List[str]] = []

        # 1. Market Scale Invariant Audit: 0 < SOM <= SAM <= TAM
        is_sizing_valid, sizing_violations = MarketSizingEngine.validate_invariants(
            tam=market.tam_estimate,
            sam=market.sam_estimate,
            som=market.som_estimate
        )
        if not is_sizing_valid:
            unsupported_claims.extend(sizing_violations)
            feedback_items.extend(sizing_violations)

        # 2. Citation Quality & Diversity Audit
        citation_report: CitationReport = self.citation_validator.validate_urls(market.source_urls)
        verified_sources_count = citation_report.valid_urls
        if citation_report.placeholder_urls > 0:
            unsupported_claims.append(f"Rejected {citation_report.placeholder_urls} placeholder/mock source URLs.")
        if verified_sources_count < self.MIN_VERIFIED_SOURCES:
            unsupported_claims.append(
                f"Insufficient citation sources: required at least {self.MIN_VERIFIED_SOURCES}, found {verified_sources_count}."
            )
        feedback_items.extend(citation_report.warnings)

        # 3. Competitor Depth Audit
        comp_report: CompetitorDepthReport = self.competitor_checker.evaluate(market.competitor_landscape)
        feedback_items.extend(comp_report.warnings)

        # 4. Factual Claim Grounding Audit
        evidence_report: EvidenceReport = self.evidence_validator.validate(
            supporting_evidence=market.supporting_evidence,
            market_trends=market.market_trends,
            source_urls=market.source_urls
        )
        unsupported_claims.extend(evidence_report.unsupported_claims)

        # 5. Calculate Composite Calibrated Confidence Score
        confidence_meta = self.confidence_scorer.compute_score(
            citation_report=citation_report,
            competitor_report=comp_report,
            evidence_report=evidence_report,
            sizing_valid=is_sizing_valid,
            agent_self_score=market.confidence_score
        )
        composite_confidence = confidence_meta["confidence_score"]

        # Deduplicate unsupported claims
        unique_unsupported = list(dict.fromkeys(unsupported_claims))

        # 6. Apply Strict 3-Point Rubric:
        # Criterion 1: composite_confidence >= 0.70
        # Criterion 2: verified_sources_count >= 2
        # Criterion 3: len(unique_unsupported) == 0
        passes_confidence = composite_confidence >= self.CONFIDENCE_PASS_THRESHOLD
        passes_sources = verified_sources_count >= self.MIN_VERIFIED_SOURCES
        passes_claims = (len(unique_unsupported) == 0)

        is_valid = passes_confidence and passes_sources and passes_claims

        # 7. Determine Validation Status & Pivot Requirements
        requires_pivot = False
        suggested_alts: List[str] = []

        if is_valid:
            status = ValidationStatus.VALID
            feedback_notes = "Validation passed all criteria: sources verified, confidence threshold met, and claims grounded."
        elif comp_report.competitor_count == 0 and not is_sizing_valid:
            # Complete absence of market signals requires fundamental venture reanalysis/pivot
            status = ValidationStatus.REANALYSIS_REQUIRED
            requires_pivot = True
            feedback_notes = "Fatal market validation failure: empty competitor landscape and invalid market sizing. Pivot required."
            suggested_alts = [
                "Re-frame the core problem statement around an adjacent, proven customer pain point.",
                "Target a narrower vertical niche with measurable commercial demand."
            ]
        elif not passes_sources or not passes_claims:
            # Citation deficiency or ungrounded claims requires targeted web research
            status = ValidationStatus.RESEARCH_REQUIRED
            requires_pivot = False
            feedback_notes = "; ".join(feedback_items) or "Additional targeted market research required to source claims."
        else:
            # Low confidence score despite basic citations
            status = ValidationStatus.LOW_CONFIDENCE
            requires_pivot = False
            feedback_notes = f"Confidence score ({composite_confidence:.2f}) is below required {self.CONFIDENCE_PASS_THRESHOLD:.2f} threshold."

        return CriticValidationOutput(
            status=status,
            confidence_score=composite_confidence,
            unsupported_claims=unique_unsupported,
            verified_sources_count=verified_sources_count,
            feedback_notes=feedback_notes,
            requires_pivot=requires_pivot,
            suggested_alternatives=suggested_alts
        )
