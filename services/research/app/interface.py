"""Research Domain Strict Interface.

Exposes public entrypoints for Market Research (Tavily search & competitor extraction)
and Critic / Evidence Validation.
All interactions from orchestrator or other agents pass through this interface.
"""

import os
import logging
from typing import Optional, List, Any

from shared.contracts.idea import FounderInput, IdeaAnalysisOutput
from shared.contracts.market import MarketResearchOutput
from shared.contracts.critic import CriticValidationOutput
from services.research.app.agents.market_research.agent import MarketResearchAgent
from services.research.app.critic.critic import CriticEngine
from services.research.app.tools.web_search import TavilySearchTool
from services.research.app.tools.search_cache import SearchCache
from services.research.app.tools.source_parser import SourceParser

logger = logging.getLogger(__name__)

# Module-level singletons
_research_agent: Optional[MarketResearchAgent] = None
_critic_engine: Optional[CriticEngine] = None


def _get_llm() -> Optional[Any]:
    """Instantiates LLM if provider credentials exist; returns None for deterministic fallback."""
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and not openai_key.startswith("your-") and openai_key != "mock":
        try:
            from langchain_openai import ChatOpenAI
            model_name = os.getenv("MARKET_RESEARCH_MODEL", os.getenv("DEFAULT_MODEL", "gpt-4o-mini"))
            return ChatOpenAI(model=model_name, api_key=openai_key, temperature=0.2)
        except Exception as e:
            logger.debug(f"[Research Interface] Could not initialize ChatOpenAI: {e}")
    return None


def get_market_research_agent() -> MarketResearchAgent:
    """Returns singleton MarketResearchAgent."""
    global _research_agent
    if _research_agent is None:
        llm = _get_llm()
        search_tool = TavilySearchTool()
        cache = SearchCache()
        parser = SourceParser()
        _research_agent = MarketResearchAgent(
            llm=llm,
            search_tool=search_tool,
            cache=cache,
            parser=parser
        )
    return _research_agent


def get_critic_engine() -> CriticEngine:
    """Returns singleton CriticEngine."""
    global _critic_engine
    if _critic_engine is None:
        _critic_engine = CriticEngine()
    return _critic_engine


async def run_market_research(
    idea: IdeaAnalysisOutput,
    founder: FounderInput,
    critique_history: Optional[List[CriticValidationOutput]] = None
) -> MarketResearchOutput:
    """Executes market research with search tools, competitor analysis, and market sizing."""
    agent = get_market_research_agent()
    return await agent.research(
        idea=idea,
        founder=founder,
        critique_history=critique_history
    )


async def run_critic_validation(
    market: MarketResearchOutput,
    idea: IdeaAnalysisOutput
) -> CriticValidationOutput:
    """Applies the strict 3-point rubric: confidence >= 0.70, >= 2 verified citations, zero unverified claims."""
    engine = get_critic_engine()
    return engine.evaluate(market=market, idea=idea)
