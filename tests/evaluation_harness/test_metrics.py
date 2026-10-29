from evaluation.metrics import (
    TokenUsage,
    calculate_citation_rate,
    calculate_cost,
    calculate_latency,
    calculate_schema_compliance,
    calculate_workflow_completion,
)
from shared.contracts.market import Competitor, MarketResearchOutput


def _market(extra_claim: bool = False) -> MarketResearchOutput:
    trends = [
        "Adoption is accelerating according to https://market-benchmarks.org/competitor-analysis",
        "Pricing pressure is rising according to https://industry-insights.io/market-report",
    ]
    evidence = [
        "Benchmark report from https://market-benchmarks.org/competitor-analysis validates demand.",
        "Industry source https://industry-insights.io/market-report confirms willingness to pay.",
    ]
    if extra_claim:
        trends.append("A large share of customers will switch immediately without evidence.")
    return MarketResearchOutput(
        competitor_landscape=[
            Competitor(name="Legacy Inc", description="Established incumbent"),
            Competitor(name="Agile Co", description="Modern challenger"),
        ],
        customer_personas=[{"role": "Operator", "pain_point": "Manual work"}],
        market_trends=trends,
        entry_barriers=["Switching costs"],
        tam_estimate=1_000_000_000.0,
        sam_estimate=100_000_000.0,
        som_estimate=10_000_000.0,
        supporting_evidence=evidence,
        source_urls=[
            "https://market-benchmarks.org/competitor-analysis",
            "https://industry-insights.io/market-report",
        ],
        confidence_score=0.9,
    )


def test_citation_rate_passes_when_all_claims_are_grounded():
    result = calculate_citation_rate([_market()])

    assert result.value == 1.0
    assert result.passed is True
    assert result.details["verified_external_citations"] == 4
    assert result.details["total_factual_market_claims"] == 4


def test_citation_rate_fails_for_ungrounded_claim():
    result = calculate_citation_rate([_market(extra_claim=True)])

    assert result.value == 0.8
    assert result.passed is False


def test_schema_compliance_uses_strict_greater_than_target():
    assert calculate_schema_compliance([True] * 20 + [False]).passed is True
    assert calculate_schema_compliance([True] * 19 + [False]).passed is False


def test_workflow_completion_uses_inclusive_target():
    assert calculate_workflow_completion([True] * 9 + [False]).passed is True
    assert calculate_workflow_completion([True] * 8 + [False, False]).passed is False


def test_latency_uses_worst_case():
    result = calculate_latency([1.0, 2.5, 0.5])

    assert result.value == 2.5
    assert result.passed is True
    assert calculate_latency([481.0]).passed is False


def test_cost_tracks_prompt_and_completion_tokens():
    result = calculate_cost(
        [TokenUsage(prompt_tokens=1_000_000, completion_tokens=1_000_000)]
    )

    assert result.value == 0.75
    assert result.passed is None
    assert result.details["total_tokens"] == 2_000_000
