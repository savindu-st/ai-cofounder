"""Hybrid Retriever with Maximal Marginal Relevance (MMR) for Startup Frameworks.

Performs query expansion and diverse document retrieval across Osterwalder BMC,
Lean Canvas, Porter/SWOT, and Curated Startup Case Studies.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import numpy as np
import logging

from services.business_intelligence.app.rag.vector_store import (
    ChromaVectorStore,
    DEFAULT_PERSIST_DIRECTORY,
    DEFAULT_COLLECTION_NAME
)

logger = logging.getLogger(__name__)

# Canonical expansion terms per Business Model Canvas block
BLOCK_EXPANSIONS = {
    "key_partners": "strategic alliances suppliers joint ventures coopetition channel partners",
    "key_activities": "core operations product development platform engineering problem solving production",
    "key_resources": "intellectual property engineering team capital proprietary algorithms data assets",
    "value_propositions": "unique value proposition UVP customer pain relief gain creators getting the job done",
    "customer_relationships": "automated self-service community customer retention dedicated support onboarding",
    "channels": "direct sales marketing channels viral loops product-led growth app store SEO distribution",
    "customer_segments": "early adopters ideal customer profile ICP target market niches multi-sided market",
    "cost_structure": "cost drivers fixed costs variable costs cloud hosting customer acquisition CAC engineering salaries",
    "revenue_streams": "subscription pricing recurring revenue tiers ARPU LTV take-rate freemium usage fees"
}


@dataclass
class RetrievedChunk:
    """Represents a retrieved document chunk with relevance context."""
    text: str
    source: str
    chunk_index: int
    distance: float
    score: float


class HybridRetriever:
    """Retrieves framework context using query expansion and MMR diversity ranking."""

    def __init__(self, vector_store: Optional[ChromaVectorStore] = None):
        self.vector_store = vector_store or ChromaVectorStore()

    def expand_query(self, query: str, block_name: Optional[str] = None) -> str:
        """Enriches the query with domain-specific terms if relevant."""
        if block_name and block_name in BLOCK_EXPANSIONS:
            return f"{query} {BLOCK_EXPANSIONS[block_name]}"
        return query

    def retrieve(
        self,
        query: str,
        block_name: Optional[str] = None,
        k: int = 5,
        mmr_lambda: float = 0.7,
        top_n: int = 3
    ) -> List[RetrievedChunk]:
        """Retrieves top_n diverse chunks using MMR algorithm over k candidates."""
        expanded_query = self.expand_query(query, block_name=block_name)
        results = self.vector_store.query(expanded_query, n_results=k)

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0] if "distances" in results and results["distances"] else [0.5] * len(documents)

        if not documents:
            return []

        # Convert raw candidates into candidate objects
        candidates: List[RetrievedChunk] = []
        for i, doc in enumerate(documents):
            meta = metadatas[i] if i < len(metadatas) else {}
            dist = distances[i] if i < len(distances) else 0.5
            # Cosine distance to similarity: sim = 1.0 - dist
            sim = max(0.0, min(1.0, 1.0 - dist))
            candidates.append(
                RetrievedChunk(
                    text=doc,
                    source=meta.get("source", "unknown"),
                    chunk_index=meta.get("chunk_index", i),
                    distance=dist,
                    score=sim
                )
            )

        if len(candidates) <= top_n:
            return candidates

        # Simple text-diversity MMR selection
        selected: List[RetrievedChunk] = []
        remaining = list(candidates)

        # Select first item with highest relevance score
        first_pick = max(remaining, key=lambda c: c.score)
        selected.append(first_pick)
        remaining.remove(first_pick)

        def jaccard_similarity(text1: str, text2: str) -> float:
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            if not words1 or not words2:
                return 0.0
            return len(words1.intersection(words2)) / len(words1.union(words2))

        # Iteratively select items balancing relevance (sim to query) and diversity (dissimilar to selected)
        while len(selected) < top_n and remaining:
            best_mmr = -float("inf")
            best_candidate = None

            for cand in remaining:
                relevance = cand.score
                max_sim_to_selected = max(jaccard_similarity(cand.text, sel.text) for sel in selected)
                mmr_score = (mmr_lambda * relevance) - ((1.0 - mmr_lambda) * max_sim_to_selected)

                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_candidate = cand

            if best_candidate:
                selected.append(best_candidate)
                remaining.remove(best_candidate)
            else:
                break

        return selected
