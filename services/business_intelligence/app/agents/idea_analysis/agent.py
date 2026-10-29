"""Idea Analysis LLM Agent.

Deconstructs founder inputs into structured assumptions, customer segments,
refined value propositions, and unfair advantages.
"""

import os
import json
import logging
from typing import Optional, Any

from shared.contracts.idea import FounderInput, IdeaAnalysisOutput
from services.business_intelligence.app.agents.idea_analysis.validator import (
    validate_founder_input
)
from services.business_intelligence.app.agents.idea_analysis.schemas import (
    IdeaDecomposition
)
from services.business_intelligence.app.agents.idea_analysis.prompts import (
    IDEA_ANALYSIS_SYSTEM_PROMPT,
    IDEA_ANALYSIS_USER_TEMPLATE
)

logger = logging.getLogger(__name__)


class IdeaAnalysisAgent:
    """Agent responsible for deconstructing raw founder ideas."""

    def __init__(self, llm: Optional[Any] = None):
        self.llm = llm

    def _fallback_decomposition(
        self,
        founder_input: FounderInput,
        warnings: list
    ) -> IdeaDecomposition:
        """Deterministic fallback when live LLM is not configured or fails."""
        market = founder_input.target_market or "Target Users"
        idea = founder_input.startup_idea

        assumptions = [
            f"Target customers in {market} experience high enough friction to adopt a new tool.",
            "Willingness to pay exists at a price point that supports sustainable customer acquisition.",
            f"Regulatory and technical feasibility allows execution within {founder_input.timeline_months} months."
        ]

        red_flags = []
        if founder_input.budget == 0.0:
            red_flags.append("Zero starting budget requires strictly organic or sweat-equity traction channels.")
        if founder_input.timeline_months < 2:
            red_flags.append("Sub-2 month runway leaves zero margin for validation pivots.")

        return IdeaDecomposition(
            problem_statement=f"Addressing operational inefficiencies for {market}: {idea}",
            target_users=[market, f"Independent operators and teams in {market}"],
            refined_value_proposition=f"Automated, intelligence-driven solution delivering {idea} with rapid time-to-value",
            key_assumptions=assumptions,
            unfair_advantages=[
                founder_input.skills_resources or "Agile founder execution and rapid feedback cycle"
            ],
            audience_personas=[],
            red_flags=red_flags,
            clarity_score=0.88,
            feasibility_score=0.85
        )

    async def analyze(self, founder_input: FounderInput) -> IdeaAnalysisOutput:
        """Deconstructs founder input into a validated IdeaAnalysisOutput."""
        sanitized_input, warnings = validate_founder_input(founder_input)

        decomposition: Optional[IdeaDecomposition] = None

        if self.llm is not None:
            try:
                user_prompt = IDEA_ANALYSIS_USER_TEMPLATE.format(
                    startup_idea=sanitized_input.startup_idea,
                    target_market=sanitized_input.target_market,
                    target_geography=sanitized_input.target_geography,
                    budget=sanitized_input.budget,
                    timeline_months=sanitized_input.timeline_months,
                    goals=sanitized_input.goals,
                    constraints=", ".join(sanitized_input.constraints),
                    skills_resources=sanitized_input.skills_resources or "None specified"
                )

                # Use structured output if available on the model
                if hasattr(self.llm, "with_structured_output"):
                    structured_llm = self.llm.with_structured_output(IdeaDecomposition)
                    decomposition = await structured_llm.ainvoke([
                        {"role": "system", "content": IDEA_ANALYSIS_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ])
                elif hasattr(self.llm, "ainvoke"):
                    resp = await self.llm.ainvoke([
                        {"role": "system", "content": IDEA_ANALYSIS_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ])
                    content = getattr(resp, "content", str(resp))
                    # Attempt JSON extraction
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()
                    data = json.loads(content)
                    decomposition = IdeaDecomposition.model_validate(data)

            except Exception as e:
                logger.warning(f"[IdeaAnalysisAgent] LLM invocation failed ({e}); using deterministic fallback.")

        if decomposition is None:
            decomposition = self._fallback_decomposition(sanitized_input, warnings)

        # Calculate composite confidence score: mean of clarity and feasibility
        confidence = round((decomposition.clarity_score + decomposition.feasibility_score) / 2.0, 2)

        return IdeaAnalysisOutput(
            problem_statement=decomposition.problem_statement,
            target_users=decomposition.target_users,
            refined_value_proposition=decomposition.refined_value_proposition,
            key_assumptions=decomposition.key_assumptions,
            red_flags=decomposition.red_flags,
            clarity_score=decomposition.clarity_score,
            feasibility_score=decomposition.feasibility_score,
            confidence_score=confidence
        )
