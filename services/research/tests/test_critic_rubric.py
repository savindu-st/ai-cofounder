"""Unit tests for the Critic & Evidence Validation Rubric Engine."""

import pytest
from services.research.app.critic.critic import CriticEngine
from shared.contracts.market import MarketResearchOutput, Competitor
from shared.enums.confidence_level import ValidationStatus


def test_critic_rubric_valid_report():
    critic = CriticEngine()
    valid_market = MarketResearchOutput(
        tam_estimate=50_000_000_000.0,
        sam_estimate=5_000_000_000.0,
        som_estimate=500_000_000.0,
        customer_personas=[{"segment": "Tech founders"}],
        competitor_landscape=[
            Competitor(
                name="Acme Inc",
                description="Enterprise market leader",
                strengths=["Large market share", "Strong distribution"],
                weaknesses=["Legacy architecture"],
                pricing_model="Enterprise SaaS ($99/user/mo)",
                website_url="https://acme.example.com"
            ),
            Competitor(
                name="Beta Tech",
                description="Modern challenger",
                strengths=["Modern UI"],
                weaknesses=["High price"],
                pricing_model="Usage-based ($49/mo)",
                website_url="https://beta.example.com"
            )
        ],
        market_trends=[
            "AI automation demand reported by gartner research",
            "Low-code adoption surveyed by statista benchmarks"
        ],
        entry_barriers=["Proprietary ML models", "Customer switching costs"],
        supporting_evidence=["Gartner report on enterprise productivity", "IDC developer survey"],
        source_urls=[
            "https://www.gartner.com/en/research",
            "https://www.statista.com/outlook/technology"
        ],
        confidence_score=0.88
    )

    result = critic.evaluate(valid_market)
    assert result.status == ValidationStatus.VALID
    assert result.confidence_score >= 0.70
    assert result.verified_sources_count >= 2
    assert len(result.unsupported_claims) == 0
    assert not result.requires_pivot


def test_critic_rubric_insufficient_sources():
    critic = CriticEngine()
    invalid_market = MarketResearchOutput(
        tam_estimate=10_000_000.0,
        sam_estimate=2_000_000.0,
        som_estimate=500_000.0,
        customer_personas=[{"segment": "Developers"}],
        competitor_landscape=[
            Competitor(
                name="SoloComp",
                description="Solo developer tool",
                strengths=["Speed"],
                weaknesses=["Features"]
            )
        ],
        market_trends=["Cloud growth"],
        entry_barriers=["Capital"],
        supporting_evidence=[],
        source_urls=["https://www.onlyonesource.com"],
        confidence_score=0.60
    )

    result = critic.evaluate(invalid_market)
    assert result.status in (ValidationStatus.RESEARCH_REQUIRED, ValidationStatus.LOW_CONFIDENCE)
    assert result.verified_sources_count < 2
    assert len(result.unsupported_claims) > 0


def test_critic_rubric_fatal_reanalysis_required():
    critic = CriticEngine()
    fatal_market = MarketResearchOutput(
        tam_estimate=100.0,
        sam_estimate=2000.0,  # Invalid: SAM > TAM
        som_estimate=50000.0, # Invalid: SOM > SAM
        customer_personas=[],
        competitor_landscape=[],  # Zero competitors
        market_trends=[],
        entry_barriers=[],
        supporting_evidence=[],
        source_urls=[],
        confidence_score=0.20
    )

    result = critic.evaluate(fatal_market)
    assert result.status == ValidationStatus.REANALYSIS_REQUIRED
    assert result.requires_pivot is True
    assert len(result.suggested_alternatives) > 0
