"""Unit tests for Web Search, Redis/Memory Search Cache, and Source Parser."""

import asyncio
import pytest
from services.research.app.tools.web_search import TavilySearchTool, SearchResult
from services.research.app.tools.search_cache import SearchCache
from services.research.app.tools.source_parser import SourceParser


def test_tavily_fallback_when_no_api_key():
    tool = TavilySearchTool(api_key=None)
    results = asyncio.run(tool.search("competitors for AI financial assistant", max_results=3))
    assert len(results) > 0
    assert all(r.is_fallback for r in results)
    assert any("competitor" in r.title.lower() or "benchmark" in r.title.lower() for r in results)


def test_tavily_specialized_methods():
    tool = TavilySearchTool(api_key="mock")
    comp_results = asyncio.run(tool.search_competitors("B2B SaaS", "DevOps AI bot"))
    assert len(comp_results) > 0
    assert comp_results[0].url.startswith("http")

    sizing_results = asyncio.run(tool.search_market_size("B2B SaaS", "Global"))
    assert len(sizing_results) > 0
    assert any("tam" in r.content.lower() or "market" in r.content.lower() for r in sizing_results)

    trend_results = asyncio.run(tool.search_trends("B2B SaaS"))
    assert len(trend_results) > 0


def test_search_cache_normalization():
    q1 = "AI market research analysis"
    q2 = "analysis research AI market"
    q3 = "   ai   market   research   analysis  "

    norm1 = SearchCache.normalize_query(q1)
    norm2 = SearchCache.normalize_query(q2)
    norm3 = SearchCache.normalize_query(q3)

    assert norm1 == norm2 == norm3
    assert SearchCache.hash_key(q1) == SearchCache.hash_key(q2) == SearchCache.hash_key(q3)


def test_search_cache_set_and_get():
    cache = SearchCache(use_in_memory_fallback=True)
    cache._redis_disabled = True  # force memory path for test isolation

    query = "enterprise SaaS market size"
    results = [
        SearchResult(
            title="SaaS Market 2025",
            url="https://saas-insights.org/report",
            content="Total market $20B with 15% CAGR",
            score=0.95,
            is_fallback=False
        )
    ]

    # Before setting
    miss = asyncio.run(cache.get(query))
    assert miss is None

    # Set and get
    asyncio.run(cache.set(query, results))
    hit = asyncio.run(cache.get(query))
    assert hit is not None
    assert len(hit) == 1
    assert hit[0].title == "SaaS Market 2025"
    assert hit[0].url == "https://saas-insights.org/report"


def test_search_cache_ttl_expiry():
    cache = SearchCache(ttl_seconds=-1, use_in_memory_fallback=True)
    cache._redis_disabled = True

    query = "expired query"
    results = [
        SearchResult(
            title="Expired Title",
            url="https://expired.org",
            content="Old content",
            score=0.8
        )
    ]

    asyncio.run(cache.set(query, results))
    # With negative TTL, get should treat it as expired
    hit = asyncio.run(cache.get(query))
    assert hit is None


def test_source_parser_html_extraction():
    parser = SourceParser()
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SaaSify - Next-Gen Operations</title>
        <meta name="description" content="SaaSify automates operations for high-growth tech startups.">
    </head>
    <body>
        <h1>Automate Everything Seamlessly</h1>
        <div class="pricing-card">
            <h3>Starter</h3>
            <span class="price">$49/month</span>
        </div>
        <div class="pricing-card">
            <h3>Enterprise</h3>
            <span class="price">$499/seat/mo</span>
        </div>
        <div class="features-section">
            <h2>Core Features</h2>
            <ul>
                <li>Automated workflow pipelines</li>
                <li>One-click cloud deployments</li>
                <li>Real-time telemetry and auditing</li>
            </ul>
        </div>
    </body>
    </html>
    """

    parsed = parser.extract_from_html(sample_html, "https://saasify.io")
    assert parsed.fetch_success is True
    assert parsed.title == "SaaSify - Next-Gen Operations"
    assert "SaaSify automates operations" in parsed.tagline
    assert len(parsed.pricing_tiers) >= 1
    assert any("$49" in p for p in parsed.pricing_tiers)
    assert len(parsed.features) >= 2
    assert any("Automated workflow" in f for f in parsed.features)


def test_source_parser_invalid_url():
    parser = SourceParser()
    parsed = asyncio.run(parser.parse_page("not_a_valid_url"))
    assert parsed.fetch_success is False
    assert "Invalid URL" in parsed.error_message
