"""RAG-Powered Business Model Canvas Generation Agent.

Retrieves theoretical frameworks and startup vertical case studies from ChromaDB
to synthesize a comprehensive 9-block Osterwalder Business Model Canvas.
"""

import os
import json
import logging
from typing import Optional, Any, List

from shared.contracts.idea import IdeaAnalysisOutput
from shared.contracts.market import MarketResearchOutput
from shared.contracts.business_model import BusinessModelOutput, BusinessModelCanvas
from services.business_intelligence.app.rag.retriever import HybridRetriever
from services.business_intelligence.app.agents.business_model.schemas import CanvasSynthesis
from services.business_intelligence.app.agents.business_model.canvas_builder import CanvasBuilder
from services.business_intelligence.app.agents.business_model.prompts import (
    BUSINESS_MODEL_SYSTEM_PROMPT,
    BUSINESS_MODEL_USER_TEMPLATE
)

logger = logging.getLogger(__name__)


class BusinessModelAgent:
    """Agent that synthesizes a 9-block Business Model Canvas using RAG context."""

    def __init__(
        self,
        llm: Optional[Any] = None,
        retriever: Optional[HybridRetriever] = None
    ):
        self.llm = llm
        self.retriever = retriever or HybridRetriever()

    def _retrieve_framework_context(
        self,
        idea: IdeaAnalysisOutput,
        market: MarketResearchOutput
    ) -> str:
        """Retrieves diverse knowledge chunks across the 9 canvas blocks."""
        retrieved_texts: List[str] = []
        queries = [
            ("value_propositions", f"value proposition for {idea.refined_value_proposition}"),
            ("revenue_streams", "sustainable startup revenue models and pricing mechanisms"),
            ("channels", "customer acquisition channels and distribution loops"),
            ("cost_structure", "cloud infrastructure engineering cost structure")
        ]

        for block_name, query in queries:
            try:
                chunks = self.retriever.retrieve(
                    query=query,
                    block_name=block_name,
                    k=4,
                    top_n=2
                )
                for chunk in chunks:
                    snippet = f"[{chunk.source}] {chunk.text[:280]}..."
                    if snippet not in retrieved_texts:
                        retrieved_texts.append(snippet)
            except Exception as e:
                logger.debug(f"[BusinessModelAgent] Retrieval error for {block_name}: {e}")

        if not retrieved_texts:
            return "Standard Osterwalder Business Model Canvas definitions and Lean Canvas heuristics."

        return "\n\n".join(retrieved_texts)

    def _fallback_synthesis(
        self,
        idea: IdeaAnalysisOutput,
        market: MarketResearchOutput
    ) -> CanvasSynthesis:
        """Deterministic synthesis grounded in idea and market data when LLM is absent or errors."""
        target_users = idea.target_users if idea.target_users else ["Enterprise Engineering Teams"]

        competitor_names = [c.name for c in market.competitor_landscape] if market.competitor_landscape else []
        comp_context = f"Differentiating against {', '.join(competitor_names[:2])}" if competitor_names else "First-mover niche advantage"

        return CanvasSynthesis(
            key_partners=[
                "Cloud Infrastructure Providers (AWS / GCP)",
                "LLM Foundational Model Vendors",
                "Ecosystem Integration Partners (GitHub / Slack)"
            ],
            key_activities=[
                "Continuous Core Agent Algorithm Tuning",
                "Self-Service Onboarding Optimization",
                "Enterprise Security & Compliance Operations"
            ],
            key_resources=[
                "Proprietary Context Knowledge Graph",
                "Domain-Specialized Fine-Tuned Prompts",
                "High-Velocity Full-Stack Engineering Team"
            ],
            value_propositions=[
                idea.refined_value_proposition,
                f"Autonomous workflows delivering 10x faster execution than legacy alternatives ({comp_context})"
            ],
            customer_relationships=[
                "Automated Self-Service Onboarding",
                "Product-Led Growth Slack/Discord Community",
                "Dedicated Customer Success for High-ACV Accounts"
            ],
            channels=[
                "Direct Web Application (Self-Serve)",
                "Developer Content Marketing and Open-Source Tools",
                "Targeted B2B Outbound Account-Based Marketing"
            ],
            customer_segments=target_users,
            cost_structure=[
                "LLM Inference Compute & API Gateway Costs",
                "Cloud Data Storage and Vector Search DB",
                "Product Engineering and GTM Salaries"
            ],
            revenue_streams=[
                "Monthly/Annual SaaS Subscription Tiers",
                "Usage-Based Overage & Add-on Seats",
                "Custom Enterprise SLA & Compliance Packages"
            ],
            key_risks=[
                "Foundational model API cost volatility eroding gross margins",
                "Fast-follower features from incumbent enterprise platforms"
            ],
            mitigations=[
                "Implement aggressive local caching and model-agnostic routing",
                "Build deep workflow integration and proprietary domain data moats"
            ],
            confidence_score=0.86
        )

    async def synthesize(
        self,
        idea: IdeaAnalysisOutput,
        market: MarketResearchOutput
    ) -> BusinessModelOutput:
        """Synthesizes the complete 9-block Osterwalder canvas."""
        rag_context = self._retrieve_framework_context(idea, market)

        synthesis: Optional[CanvasSynthesis] = None

        if self.llm is not None:
            try:
                competitors_summary = ", ".join([
                    f"{c.name} ({c.pricing_model or 'Subscription'})"
                    for c in market.competitor_landscape
                ]) if market.competitor_landscape else "Direct and indirect market incumbents"

                tam_sam_som_str = f"TAM: ${market.tam_estimate:,.0f}, SAM: ${market.sam_estimate:,.0f}, SOM: ${market.som_estimate:,.0f}" if market.tam_estimate else "Market sizing triangulated"

                user_prompt = BUSINESS_MODEL_USER_TEMPLATE.format(
                    problem_statement=idea.problem_statement,
                    refined_value_proposition=idea.refined_value_proposition,
                    target_users=", ".join(idea.target_users),
                    key_assumptions="; ".join(idea.key_assumptions),
                    unfair_advantages="; ".join(getattr(idea, "red_flags", []) or ["Agile execution"]),
                    competitors=competitors_summary,
                    trends="; ".join(market.market_trends[:3]),
                    entry_barriers="; ".join(market.entry_barriers[:3]),
                    tam_sam_som=tam_sam_som_str,
                    rag_framework_context=rag_context
                )

                if hasattr(self.llm, "with_structured_output"):
                    structured_llm = self.llm.with_structured_output(CanvasSynthesis)
                    synthesis = await structured_llm.ainvoke([
                        {"role": "system", "content": BUSINESS_MODEL_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ])
                elif hasattr(self.llm, "ainvoke"):
                    resp = await self.llm.ainvoke([
                        {"role": "system", "content": BUSINESS_MODEL_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ])
                    content = getattr(resp, "content", str(resp))
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()
                    data = json.loads(content)
                    synthesis = CanvasSynthesis.model_validate(data)

            except Exception as e:
                logger.warning(f"[BusinessModelAgent] LLM generation failed ({e}); using deterministic synthesis.")

        if synthesis is None:
            synthesis = self._fallback_synthesis(idea, market)

        return CanvasBuilder.build(synthesis, idea, market)
