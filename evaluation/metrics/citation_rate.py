"""Citation coverage metric.

Measures the share of factual market claims that are grounded in verified
external sources. A claim is counted as cited only when its supporting URL
passes the project's citation validator and the evidence validator can match
the claim back to that source.
"""

from typing import Iterable, List, Optional

from evaluation.metrics.base import MetricResult
from shared.contracts.market import MarketResearchOutput
from services.research.app.critic.citation_validator import CitationValidator
from services.research.app.critic.evidence_validator import EvidenceValidator

TARGET = 1.0


def _verified_sources(urls: Iterable[str]) -> List[str]:
    validator = CitationValidator()
    verified: List[str] = []
    for url in urls:
        result = validator.validate_single_url(url)
        if result.is_valid_format and result.is_secure_https and not result.is_placeholder:
            verified.append(url)
    return verified


def calculate(markets: Iterable[Optional[MarketResearchOutput]]) -> MetricResult:
    """Return the aggregate citation rate across one or more market outputs."""
    evidence_validator = EvidenceValidator()
    total_claims = 0
    grounded_claims = 0
    verified_source_count = 0
    scenarios = 0

    for market in markets:
        if market is None:
            continue
        scenarios += 1
        sources = _verified_sources(market.source_urls)
        verified_source_count += len(sources)
        report = evidence_validator.validate(
            supporting_evidence=market.supporting_evidence,
            market_trends=market.market_trends,
            source_urls=sources,
        )
        total_claims += report.total_claims
        grounded_claims += report.grounded_claims

    value = grounded_claims / total_claims if total_claims else 0.0
    passed = total_claims > 0 and value >= TARGET

    return MetricResult(
        name="Citation Rate",
        value=round(value, 4),
        display=f"{value:.1%}",
        target="100%",
        passed=passed,
        details={
            "verified_external_citations": grounded_claims,
            "total_factual_market_claims": total_claims,
            "verified_source_urls": verified_source_count,
            "scenarios_with_market_data": scenarios,
        },
    )
