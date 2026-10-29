"""Revenue Parameter Extraction Agent.

Phase 1 of the hybrid finance architecture: the LLM (when configured) extracts
numerical assumptions only. A deterministic fallback keeps the pipeline fully
functional offline and in CI.
"""

import json
import logging
import re
import statistics
from typing import Any, List, Optional

from shared.contracts.business_model import BusinessModelOutput
from shared.contracts.idea import FounderInput, IdeaAnalysisOutput
from shared.contracts.market import MarketResearchOutput

try:
    from services.finance.app.agents.revenue_estimation.prompts import (
        FINANCIAL_EXTRACTION_SYSTEM_PROMPT,
        FINANCIAL_EXTRACTION_USER_TEMPLATE,
    )
    from services.finance.app.agents.revenue_estimation.schemas import (
        ExtractedFinancialParameters,
    )
except ImportError:  # pragma: no cover
    from app.agents.revenue_estimation.prompts import (
        FINANCIAL_EXTRACTION_SYSTEM_PROMPT,
        FINANCIAL_EXTRACTION_USER_TEMPLATE,
    )
    from app.agents.revenue_estimation.schemas import ExtractedFinancialParameters

logger = logging.getLogger(__name__)

_PRICE_PATTERN = re.compile(r"\$\s*([0-9]{1,5}(?:\.[0-9]{1,2})?)")


class RevenueParameterAgent:
    """Extracts pricing, growth, churn, COGS, CAC, and capital assumptions."""

    def __init__(self, llm: Optional[Any] = None):
        self.llm = llm

    def extract(
        self,
        idea: IdeaAnalysisOutput,
        market: MarketResearchOutput,
        business_model: BusinessModelOutput,
        founder: Optional[FounderInput] = None,
        retune_notes: Optional[str] = None,
        retune_round: int = 0,
    ) -> ExtractedFinancialParameters:
        if self.llm is not None:
            extracted = self._extract_with_llm(
                idea=idea,
                market=market,
                business_model=business_model,
                founder=founder,
                retune_notes=retune_notes,
            )
            if extracted is not None:
                return self._apply_retune(extracted, retune_round)

        fallback = self._deterministic_fallback(
            idea=idea,
            market=market,
            business_model=business_model,
            founder=founder,
            retune_notes=retune_notes,
        )
        return self._apply_retune(fallback, retune_round)

    def _extract_with_llm(
        self,
        idea: IdeaAnalysisOutput,
        market: MarketResearchOutput,
        business_model: BusinessModelOutput,
        founder: Optional[FounderInput],
        retune_notes: Optional[str],
    ) -> Optional[ExtractedFinancialParameters]:
        try:
            prompt = FINANCIAL_EXTRACTION_USER_TEMPLATE.format(
                startup_idea=(founder.startup_idea if founder else idea.refined_value_proposition),
                problem_statement=idea.problem_statement,
                target_users=", ".join(idea.target_users) or "General market",
                revenue_streams="; ".join(business_model.canvas.revenue_streams) or "Not specified",
                cost_structure="; ".join(business_model.canvas.cost_structure) or "Not specified",
                tam=market.tam_estimate or 0.0,
                sam=market.sam_estimate or 0.0,
                som=market.som_estimate or 0.0,
                competitor_pricing="; ".join(
                    c.pricing_model for c in market.competitor_landscape if c.pricing_model
                ) or "No explicit competitor pricing",
                budget=(founder.budget if founder else 0.0),
                geography=(founder.target_geography if founder else "Global"),
                retune_notes=retune_notes or "None",
            )
            raw: Any = None
            if hasattr(self.llm, "generate_json"):
                raw = self.llm.generate_json(
                    prompt=f"{FINANCIAL_EXTRACTION_SYSTEM_PROMPT}\n\n{prompt}",
                    schema=ExtractedFinancialParameters,
                )
            elif hasattr(self.llm, "invoke"):
                response = self.llm.invoke(
                    [
                        {"role": "system", "content": FINANCIAL_EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ]
                )
                content = getattr(response, "content", str(response))
                raw = self._parse_json_content(content)

            if not isinstance(raw, dict) or not raw:
                return None
            return ExtractedFinancialParameters.from_raw(raw)
        except Exception as exc:
            logger.warning("[RevenueParameterAgent] LLM extraction failed (%s); using fallback.", exc)
            return None

    @staticmethod
    def _parse_json_content(content: str) -> Optional[dict]:
        try:
            if "```json" in content:
                content = content.split("```json", 1)[1].split("```", 1)[0]
            elif "```" in content:
                content = content.split("```", 1)[1].split("```", 1)[0]
            parsed = json.loads(content.strip())
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    @staticmethod
    def _classify(text: str) -> str:
        lower = text.lower()
        if any(token in lower for token in ("hardware", "device", "iot", "sensor", "robot")):
            return "hardware"
        if any(token in lower for token in ("marketplace", "two-sided", "gig", "matching platform")):
            return "marketplace"
        if any(token in lower for token in ("developer", "devtools", "sdk", "api", "code review", "cli")):
            return "devtools"
        if any(token in lower for token in ("consumer", "mobile app", "student", "laundry", "food delivery", "d2c")):
            return "consumer"
        return "b2b"

    @classmethod
    def _estimate_price(cls, texts: List[str]) -> Optional[float]:
        candidates: List[float] = []
        for text in texts:
            for match in _PRICE_PATTERN.finditer(text or ""):
                value = float(match.group(1))
                if 5.0 <= value <= 5000.0:
                    candidates.append(value)
        if not candidates:
            return None
        return round(statistics.median(candidates), 2)

    def _deterministic_fallback(
        self,
        idea: IdeaAnalysisOutput,
        market: MarketResearchOutput,
        business_model: BusinessModelOutput,
        founder: Optional[FounderInput],
        retune_notes: Optional[str],
    ) -> ExtractedFinancialParameters:
        text = " ".join(
            [
                idea.problem_statement,
                idea.refined_value_proposition,
                " ".join(idea.target_users),
                " ".join(business_model.canvas.revenue_streams),
                founder.target_market if founder else "",
            ]
        )
        archetype = self._classify(text)

        profiles = {
            "b2b": {"price": 149.0, "growth": 0.12, "churn": 0.02, "cogs_ratio": 0.20},
            "devtools": {"price": 79.0, "growth": 0.18, "churn": 0.04, "cogs_ratio": 0.15},
            "consumer": {"price": 19.0, "growth": 0.22, "churn": 0.07, "cogs_ratio": 0.40},
            "marketplace": {"price": 39.0, "growth": 0.16, "churn": 0.06, "cogs_ratio": 0.35},
            "hardware": {"price": 299.0, "growth": 0.08, "churn": 0.02, "cogs_ratio": 0.55},
        }
        profile = profiles[archetype]

        pricing_texts = list(business_model.canvas.revenue_streams)
        pricing_texts.extend(
            competitor.pricing_model
            for competitor in market.competitor_landscape
            if competitor.pricing_model
        )
        extracted_price = self._estimate_price(pricing_texts)
        price = extracted_price if extracted_price is not None else profile["price"]

        som = float(market.som_estimate or 0.0)
        annual_contract_value = max(1.0, price * 12.0)
        addressable_customers = som / annual_contract_value if som > 0 else 0.0
        starting_customers = int(min(500, max(5, round(addressable_customers * 0.005))))

        cogs_per_unit = round(price * profile["cogs_ratio"], 2)
        fixed_monthly_costs = round(max(2500.0, starting_customers * price * 0.35), 2)
        cac = round(min(1000.0, max(25.0, price * 1.5)), 2)
        budget = float(founder.budget) if founder and founder.budget > 0 else 0.0
        starting_capital = round(budget if budget > 0 else max(50000.0, fixed_monthly_costs * 6.0), 2)

        assumptions = [
            f"Deterministic fallback archetype: {archetype}.",
            f"Monthly price set to ${price:,.2f} based on pricing evidence or archetype benchmark.",
            f"Starting customer base estimated from SOM (${som:,.0f}) and annual contract value.",
            f"Monthly growth {profile['growth'] * 100:.1f}% and churn {profile['churn'] * 100:.1f}% from archetype benchmarks.",
        ]
        if retune_notes:
            assumptions.append(f"Retune context applied: {retune_notes[:160]}")

        return ExtractedFinancialParameters.from_raw(
            {
                "monthly_price": price,
                "starting_customers": starting_customers,
                "monthly_growth_rate": profile["growth"],
                "monthly_churn_rate": profile["churn"],
                "cogs_per_unit": cogs_per_unit,
                "fixed_monthly_costs": fixed_monthly_costs,
                "cac": cac,
                "starting_capital": starting_capital,
                "assumptions": assumptions,
                "confidence": round(min(0.9, max(0.6, idea.confidence_score)), 2),
            }
        )

    @staticmethod
    def _apply_retune(
        extracted: ExtractedFinancialParameters,
        retune_round: int,
    ) -> ExtractedFinancialParameters:
        """Tightens pricing/churn/CAC assumptions on repeated finance retunes."""
        if retune_round <= 0:
            return extracted

        price = extracted.monthly_price * (1.10 ** retune_round)
        churn = max(0.005, extracted.monthly_churn_rate * (0.85 ** retune_round))
        cac = extracted.cac * (0.80 ** retune_round)

        return ExtractedFinancialParameters.from_raw(
            {
                "monthly_price": price,
                "starting_customers": extracted.starting_customers,
                "monthly_growth_rate": extracted.monthly_growth_rate,
                "monthly_churn_rate": churn,
                "cogs_per_unit": min(extracted.cogs_per_unit, price * 0.95),
                "fixed_monthly_costs": extracted.fixed_monthly_costs,
                "cac": cac,
                "starting_capital": extracted.starting_capital,
                "assumptions": extracted.assumptions
                + [f"Finance retune round {retune_round}: tightened price/churn/CAC assumptions."],
                "confidence": extracted.confidence,
            }
        )
