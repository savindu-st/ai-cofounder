"""Unit tests for Business Model Canvas Agent and Canvas Builder."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from shared.contracts.idea import IdeaAnalysisOutput
from shared.contracts.market import MarketResearchOutput, Competitor
from shared.contracts.business_model import BusinessModelCanvas, BusinessModelOutput
from services.business_intelligence.app.agents.business_model.schemas import CanvasSynthesis
from services.business_intelligence.app.agents.business_model.canvas_builder import CanvasBuilder
from services.business_intelligence.app.agents.business_model.agent import BusinessModelAgent


@pytest.fixture
def sample_idea():
    return IdeaAnalysisOutput(
        problem_statement="Engineers spend 10h/week on manual API documentation maintenance.",
        target_users=["API Developers", "Technical Writers"],
        refined_value_proposition="Autonomous documentation syncing from Git commit diffs.",
        key_assumptions=[
            "Teams are willing to pay for automated API sync",
            "Git webhooks provide sufficient schema context"
        ],
        red_flags=[],
        clarity_score=0.90,
        feasibility_score=0.85,
        confidence_score=0.88
    )


@pytest.fixture
def sample_market():
    return MarketResearchOutput(
        competitor_landscape=[
            Competitor(
                name="SwaggerHub",
                description="Manual OpenAPI editing and team collaboration",
                strengths=["Enterprise brand", "Standard conformity"],
                weaknesses=["Manual workflows", "Clunky UI"],
                pricing_model="Per-user SaaS"
            )
        ],
        customer_personas=[{"title": "Lead API Architect"}],
        market_trends=["Shift toward spec-driven development"],
        entry_barriers=["Integration depth with legacy tools"],
        tam_estimate=5000000000.0,
        sam_estimate=1200000000.0,
        som_estimate=60000000.0,
        confidence_score=0.82
    )


def test_canvas_builder_consistency_valid(sample_idea, sample_market):
    synthesis = CanvasSynthesis(
        key_partners=["GitHub", "GitLab"],
        key_activities=["Parser optimization", "Developer advocacy"],
        key_resources=["Proprietary diff parser", "Cloud infrastructure"],
        value_propositions=[sample_idea.refined_value_proposition],
        customer_relationships=["Self-service PLG", "Discord community"],
        channels=["Direct web app", "GitHub Marketplace"],
        customer_segments=sample_idea.target_users,
        cost_structure=["AWS compute", "Engineering salaries"],
        revenue_streams=["Subscription SaaS ($49/seat/mo)"],
        key_risks=["API spec breaking changes"],
        mitigations=["Schema drift detection"],
        confidence_score=0.88
    )

    output = CanvasBuilder.build(synthesis, sample_idea, sample_market)
    assert isinstance(output, BusinessModelOutput)
    assert len(output.canvas.key_partners) == 2
    assert len(output.canvas.revenue_streams) == 1
    assert output.confidence_score == 0.88


def test_canvas_builder_consistency_warning(sample_idea, sample_market):
    canvas = BusinessModelCanvas(
        key_partners=["GitHub"],
        key_activities=["Code maintenance"],
        key_resources=["Servers"],
        value_propositions=["Fast docs"],
        customer_relationships=["None"],
        channels=["Retail stores"],  # Mismatched channel for SaaS
        customer_segments=["Doctors and Nurses"],  # Mismatched segment
        cost_structure=["Office rent"],
        revenue_streams=["Subscription SaaS"]
    )

    is_valid, warnings = CanvasBuilder.verify_consistency(canvas, sample_idea, sample_market)
    assert is_valid is False
    assert any("Customer segments in canvas do not explicitly reflect" in w for w in warnings)


def test_business_model_agent_deterministic_fallback(sample_idea, sample_market):
    async def _run():
        agent = BusinessModelAgent(llm=None, retriever=None)
        output = await agent.synthesize(sample_idea, sample_market)

        assert isinstance(output, BusinessModelOutput)
        assert output.canvas is not None
        assert len(output.canvas.value_propositions) >= 1
        assert len(output.canvas.cost_structure) >= 1
        assert len(output.canvas.revenue_streams) >= 1
        assert output.confidence_score >= 0.70

    asyncio.run(_run())
