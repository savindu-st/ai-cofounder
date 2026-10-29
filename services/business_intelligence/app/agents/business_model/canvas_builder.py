"""Canvas Builder and Consistency Verification for Osterwalder BMC."""

from typing import Tuple, List
from shared.contracts.business_model import BusinessModelCanvas, BusinessModelOutput
from shared.contracts.idea import IdeaAnalysisOutput
from shared.contracts.market import MarketResearchOutput
from services.business_intelligence.app.agents.business_model.schemas import CanvasSynthesis


class CanvasBuilder:
    """Builds and verifies Osterwalder Business Model Canvas integrity."""

    @staticmethod
    def verify_consistency(
        canvas: BusinessModelCanvas,
        idea: IdeaAnalysisOutput,
        market: MarketResearchOutput
    ) -> Tuple[bool, List[str]]:
        """Verifies structural and semantic consistency across BMC blocks."""
        warnings: List[str] = []

        # 1. Check for empty blocks
        blocks = {
            "key_partners": canvas.key_partners,
            "key_activities": canvas.key_activities,
            "key_resources": canvas.key_resources,
            "value_propositions": canvas.value_propositions,
            "customer_relationships": canvas.customer_relationships,
            "channels": canvas.channels,
            "customer_segments": canvas.customer_segments,
            "cost_structure": canvas.cost_structure,
            "revenue_streams": canvas.revenue_streams,
        }
        for name, items in blocks.items():
            if not items:
                warnings.append(f"Block '{name}' has no entries.")

        # 2. Segment alignment: Canvas customer segments should overlap with idea target users
        if idea.target_users and canvas.customer_segments:
            seg_text = " ".join(canvas.customer_segments).lower()
            overlap = any(user.lower() in seg_text for user in idea.target_users)
            if not overlap:
                warnings.append(
                    "Customer segments in canvas do not explicitly reflect target users from Idea Analysis."
                )

        # 3. Monetization alignment: If revenue streams mention 'subscription', channels should support self-service or direct sales
        rev_text = " ".join(canvas.revenue_streams).lower()
        chan_text = " ".join(canvas.channels).lower()
        if "subscription" in rev_text or "saas" in rev_text:
            if not any(k in chan_text for k in ["web", "app", "direct", "plg", "self-serve", "online", "sales"]):
                warnings.append("Subscription model without clear digital or direct sales channels identified.")

        is_valid = len(warnings) == 0
        return is_valid, warnings

    @staticmethod
    def build(
        synthesis: CanvasSynthesis,
        idea: IdeaAnalysisOutput,
        market: MarketResearchOutput
    ) -> BusinessModelOutput:
        """Constructs and validates a BusinessModelOutput contract."""
        canvas = BusinessModelCanvas(
            key_partners=synthesis.key_partners,
            key_activities=synthesis.key_activities,
            key_resources=synthesis.key_resources,
            value_propositions=synthesis.value_propositions,
            customer_relationships=synthesis.customer_relationships,
            channels=synthesis.channels,
            customer_segments=synthesis.customer_segments,
            cost_structure=synthesis.cost_structure,
            revenue_streams=synthesis.revenue_streams
        )

        _, warnings = CanvasBuilder.verify_consistency(canvas, idea, market)

        # If any warnings exist, include them in mitigations or key risks
        risks = list(synthesis.key_risks)
        mitigations = list(synthesis.mitigations)
        if warnings:
            risks.extend([f"Alignment Advisory: {w}" for w in warnings[:2]])

        return BusinessModelOutput(
            framework_used="Osterwalder Business Model Canvas (BMC)",
            canvas=canvas,
            key_risks=risks,
            mitigations=mitigations,
            confidence_score=synthesis.confidence_score
        )
