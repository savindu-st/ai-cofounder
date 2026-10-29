"""Unit tests for Idea Analysis Agent and Input Validator."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from shared.contracts.idea import FounderInput, IdeaAnalysisOutput
from services.business_intelligence.app.agents.idea_analysis.validator import (
    validate_founder_input,
    IdeaValidationError
)
from services.business_intelligence.app.agents.idea_analysis.schemas import (
    IdeaDecomposition
)
from services.business_intelligence.app.agents.idea_analysis.agent import (
    IdeaAnalysisAgent
)


def test_validator_valid_input():
    founder = FounderInput(
        startup_idea="Automated AI meeting summary and action item tracker for engineering teams",
        target_market="Engineering Managers",
        budget=10000.0,
        timeline_months=6
    )
    sanitized, warnings = validate_founder_input(founder)
    assert sanitized.startup_idea == founder.startup_idea
    assert sanitized.target_market == "Engineering Managers"
    assert sanitized.budget == 10000.0
    assert sanitized.timeline_months == 6
    assert len(warnings) == 0


def test_validator_rejects_empty_idea():
    founder = FounderInput(
        startup_idea="   ",
        target_market="DevOps"
    )
    with pytest.raises(IdeaValidationError) as exc_info:
        validate_founder_input(founder)
    assert "Startup idea cannot be empty" in str(exc_info.value)


def test_validator_rejects_short_idea():
    founder = FounderInput(
        startup_idea="Short",
        target_market="DevOps"
    )
    with pytest.raises(IdeaValidationError) as exc_info:
        validate_founder_input(founder)
    assert "too short" in str(exc_info.value)


def test_validator_clamps_negative_budget():
    founder = FounderInput(
        startup_idea="Valid long startup idea description here for testing",
        target_market="DevOps",
        budget=-500.0
    )
    sanitized, warnings = validate_founder_input(founder)
    assert sanitized.budget == 0.0
    assert any("clamped to $0.00" in w for w in warnings)


def test_validator_clamps_extreme_timeline():
    founder = FounderInput(
        startup_idea="Valid long startup idea description here for testing",
        target_market="DevOps",
        timeline_months=120
    )
    sanitized, warnings = validate_founder_input(founder)
    assert sanitized.timeline_months == 60
    assert any("clamped to 60 months" in w for w in warnings)


def test_idea_analysis_agent_deterministic_fallback():
    async def _run():
        agent = IdeaAnalysisAgent(llm=None)
        founder = FounderInput(
            startup_idea="AI code review bot that prevents security leaks in PRs",
            target_market="Software Developers",
            budget=5000.0,
            timeline_months=3
        )
        output = await agent.analyze(founder)
        assert isinstance(output, IdeaAnalysisOutput)
        assert "code review" in output.problem_statement.lower()
        assert len(output.target_users) >= 1
        assert len(output.key_assumptions) >= 2
        assert output.clarity_score > 0.0
        assert output.confidence_score >= 0.70

    asyncio.run(_run())


def test_idea_analysis_agent_with_mock_llm():
    async def _run():
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
            return_value=IdeaDecomposition(
                problem_statement="Engineers spend 20% of their time fixing syntax bugs manually.",
                target_users=["Full-Stack Engineers", "Tech Leads"],
                refined_value_proposition="Instant zero-shot syntax remediation inside git hooks.",
                key_assumptions=[
                    "Developers trust automated formatting in commit hooks",
                    "Willingness to pay exists via team-wide SaaS subscription"
                ],
                unfair_advantages=["Proprietary AST parsing algorithms"],
                red_flags=[],
                clarity_score=0.95,
                feasibility_score=0.90
            )
        )

        agent = IdeaAnalysisAgent(llm=mock_llm)
        founder = FounderInput(
            startup_idea="Instant syntax remediation tool integrated with git hooks",
            target_market="Full-Stack Developers"
        )
        output = await agent.analyze(founder)
        assert output.clarity_score == 0.95
        assert output.confidence_score == pytest.approx(0.93, abs=0.01)
        assert "Instant zero-shot syntax remediation" in output.refined_value_proposition

    asyncio.run(_run())
