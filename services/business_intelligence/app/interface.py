"""Business Intelligence Domain Strict Interface.

Exposes public entrypoints for Idea Analysis and RAG-powered Business Model Canvas synthesis.
All interactions from orchestrator or other agents pass through this interface.
"""

import os
import logging
from typing import Optional, Any

from shared.contracts.idea import FounderInput, IdeaAnalysisOutput
from shared.contracts.market import MarketResearchOutput
from shared.contracts.business_model import BusinessModelOutput
from services.business_intelligence.app.agents.idea_analysis.agent import IdeaAnalysisAgent
from services.business_intelligence.app.agents.business_model.agent import BusinessModelAgent
from services.business_intelligence.app.rag.retriever import HybridRetriever
from services.business_intelligence.app.rag.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)

# Module-level singletons
_idea_agent: Optional[IdeaAnalysisAgent] = None
_bm_agent: Optional[BusinessModelAgent] = None


def _get_llm() -> Optional[Any]:
    """Instantiates LLM if provider credentials exist; returns None for deterministic fallback."""
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and not openai_key.startswith("your-"):
        try:
            from langchain_openai import ChatOpenAI
            model_name = os.getenv("IDEA_ANALYSIS_MODEL", os.getenv("DEFAULT_MODEL", "gpt-4o-mini"))
            return ChatOpenAI(model=model_name, api_key=openai_key, temperature=0.2)
        except Exception as e:
            logger.debug(f"[BI Interface] Could not load ChatOpenAI: {e}")
    return None


def get_idea_analysis_agent() -> IdeaAnalysisAgent:
    """Returns singleton IdeaAnalysisAgent."""
    global _idea_agent
    if _idea_agent is None:
        llm = _get_llm()
        _idea_agent = IdeaAnalysisAgent(llm=llm)
    return _idea_agent


def get_business_model_agent() -> BusinessModelAgent:
    """Returns singleton BusinessModelAgent with configured RAG retriever."""
    global _bm_agent
    if _bm_agent is None:
        llm = _get_llm()
        vector_store = ChromaVectorStore()
        retriever = HybridRetriever(vector_store=vector_store)
        _bm_agent = BusinessModelAgent(llm=llm, retriever=retriever)
    return _bm_agent


async def run_idea_analysis(founder_input: FounderInput) -> IdeaAnalysisOutput:
    """Deconstructs founder input into core assumptions, value proposition, and customer segments."""
    agent = get_idea_analysis_agent()
    return await agent.analyze(founder_input)


async def run_business_model(
    idea: IdeaAnalysisOutput,
    market: MarketResearchOutput
) -> BusinessModelOutput:
    """Synthesizes the 9 Business Model Canvas blocks using ChromaDB RAG and market data."""
    agent = get_business_model_agent()
    return await agent.synthesize(idea, market)
