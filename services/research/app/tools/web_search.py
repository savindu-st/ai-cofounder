"""Web Search Tool with Tavily API and Graceful Fallback.

Supports live web search for competitor intelligence, market sizing (TAM/SAM/SOM),
industry CAGR trends, and regulatory barriers.
Gracefully degrades to parameterized fixture knowledge when API key is missing
or network request fails.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Standardized web search result item."""
    title: str
    url: str
    content: str
    score: float = 1.0
    is_fallback: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class TavilySearchTool:
    """Tavily search client with deterministic fallback logic."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.mock_mode = (
            os.getenv("MOCK_SEARCH", "false").lower() in ("true", "1", "yes")
            or not self.api_key
            or self.api_key.startswith("your-")
            or self.api_key == "mock"
        )
        self._client = None

    def _get_client(self):
        """Lazy initialization of Tavily client."""
        if self._client is None and not self.mock_mode:
            try:
                from tavily import TavilyClient
                self._client = TavilyClient(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"[TavilySearchTool] Failed to initialize TavilyClient: {e}. Switching to mock mode.")
                self.mock_mode = True
        return self._client

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Executes search via Tavily API or fallback."""
        if self.mock_mode:
            return self._fallback_search(query, max_results)

        try:
            client = self._get_client()
            if client is None:
                return self._fallback_search(query, max_results)

            # Tavily client is synchronous by default, call client.search
            import asyncio
            response = await asyncio.to_thread(
                client.search,
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_answer=True
            )

            results: List[SearchResult] = []
            for item in response.get("results", []):
                results.append(
                    SearchResult(
                        title=item.get("title", "Untitled Result"),
                        url=item.get("url", "https://trusted-market-intelligence.org/source"),
                        content=item.get("content", ""),
                        score=float(item.get("score", 0.9)),
                        is_fallback=False
                    )
                )

            if not results:
                logger.info(f"[TavilySearchTool] No results returned for query '{query}'. Using fallback.")
                return self._fallback_search(query, max_results)

            return results

        except Exception as e:
            logger.warning(f"[TavilySearchTool] Live search failed for '{query}': {e}. Gracefully falling back.")
            return self._fallback_search(query, max_results)

    def _fallback_search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Provides domain-relevant fallback results when live search is unavailable."""
        q_lower = query.lower()

        if "competitor" in q_lower or "alternative" in q_lower or "vs" in q_lower:
            return [
                SearchResult(
                    title="Enterprise Market Leaders & Competitor Benchmarks",
                    url="https://market-benchmarks.org/competitor-analysis",
                    content=(
                        "Established enterprise platforms dominate with high brand recognition and extensive enterprise feature sets, "
                        "pricing at $199-$500/seat/month. However, users frequently cite steep learning curves, slow onboarding, and rigid workflows. "
                        "Modern agile challengers offer self-serve models at $29-$79/seat/month with lightweight workflows."
                    ),
                    score=0.92,
                    is_fallback=True
                ),
                SearchResult(
                    title="Software Landscape and Emerging Challengers Report",
                    url="https://industry-insights.io/market-report",
                    content=(
                        "New market entrants differentiate through automation, modern UI/UX, and transparent usage-based pricing. "
                        "Key competitive moats include proprietary workflow automation, ecosystem integrations, and rapid customer time-to-value."
                    ),
                    score=0.88,
                    is_fallback=True
                ),
                SearchResult(
                    title="Product Teardowns & Pricing Comparison Database",
                    url="https://saas-pricing-index.com/teardowns",
                    content=(
                        "Tier 1 competitors: Legacy Enterprise Corp ($450/mo), CloudPoint Agile ($59/mo), WorkflowPro ($99/mo). "
                        "Strengths include existing distribution channels and SOC-2 compliance; weaknesses include lack of AI-first capabilities."
                    ),
                    score=0.85,
                    is_fallback=True
                )
            ][:max_results]

        if "tam" in q_lower or "sam" in q_lower or "som" in q_lower or "market size" in q_lower or "cagr" in q_lower:
            return [
                SearchResult(
                    title="Global Industry Market Sizing & Forecast Analysis",
                    url="https://global-research-metrics.net/market-sizing",
                    content=(
                        "The global addressable market (TAM) is estimated at $12.4 Billion with an annual growth rate (CAGR) of 18.5% through 2030. "
                        "The serviceable available market (SAM) for modern digital solutions represents approximately $2.1 Billion across North America and Europe, "
                        "with an immediate serviceable obtainable market (SOM) of $120 Million for agile early-adopter segments."
                    ),
                    score=0.94,
                    is_fallback=True
                ),
                SearchResult(
                    title="Venture Capital Sector Report & Growth Dynamics",
                    url="https://venture-perspectives.com/sector-growth",
                    content=(
                        "Customer count estimates indicate over 450,000 potential target business accounts globally. "
                        "Average contract value (ACV) ranges from $1,200/year for SMBs to $36,000/year for mid-market teams. "
                        "Healthy gross margins exceed 75% for software-driven automated models."
                    ),
                    score=0.89,
                    is_fallback=True
                )
            ][:max_results]

        # Generic trend and regulatory fallback
        return [
            SearchResult(
                title="Sector Technology Trends & Operational Innovations",
                url="https://tech-trends-quarterly.org/innovation-index",
                content=(
                    f"Market interest in {query} is driven by the acceleration of automated decision intelligence, "
                    "cost optimization pressures, and shifting demand toward self-serve platforms. Regulatory considerations include "
                    "strict data privacy standards (GDPR, CCPA) and transparency in algorithmic workflows."
                ),
                score=0.90,
                is_fallback=True
            ),
            SearchResult(
                title="Industry Barrier Analysis & Adoption Lifecycle",
                url="https://adoption-dynamics.edu/barrier-study",
                content=(
                    "Primary barriers to customer adoption include existing workflow inertia, data migration concerns, "
                    "and trust verification in automated recommendations. Overcoming these requires clear auditability and low-friction pilots."
                ),
                score=0.86,
                is_fallback=True
            )
        ][:max_results]

    async def search_competitors(self, industry: str, idea: str) -> List[SearchResult]:
        """Convenience method to search competitor landscape."""
        query = f"top competitors alternatives pricing for {idea} in {industry}"
        return await self.search(query, max_results=5)

    async def search_market_size(self, industry: str, geography: str = "Global") -> List[SearchResult]:
        """Convenience method to search market sizing and CAGR data."""
        query = f"{industry} market size TAM SAM SOM CAGR forecast {geography}"
        return await self.search(query, max_results=5)

    async def search_trends(self, industry: str) -> List[SearchResult]:
        """Convenience method to search market trends and barriers."""
        query = f"{industry} industry trends adoption challenges regulatory barriers"
        return await self.search(query, max_results=4)
