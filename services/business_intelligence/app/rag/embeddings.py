"""Embeddings Manager for Business Intelligence RAG.

Provides embedding functions with fallback mechanisms:
1. SentenceTransformer / ONNX MiniLM local embeddings (fast, zero API cost)
2. OpenAI embeddings fallback (when OPENAI_API_KEY is configured)
3. Default ChromaDB embedding function as safe resilience fallback
"""

import os
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

_embedding_instance: Optional[Any] = None


def get_embedding_function():
    """Returns a singleton Chroma-compatible embedding function."""
    global _embedding_instance
    if _embedding_instance is not None:
        return _embedding_instance

    # 1. Try local SentenceTransformer or ONNX MiniLM (preferred for offline/deterministic)
    try:
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
        _embedding_instance = ONNXMiniLM_L6_V2()
        logger.info("[Embeddings] Initialized ONNXMiniLM_L6_V2 local embeddings.")
        return _embedding_instance
    except Exception as e:
        logger.debug(f"[Embeddings] ONNXMiniLM_L6_V2 not available: {e}")

    try:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        _embedding_instance = SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        logger.info("[Embeddings] Initialized SentenceTransformer (all-MiniLM-L6-v2).")
        return _embedding_instance
    except Exception as e:
        logger.debug(f"[Embeddings] SentenceTransformer not available: {e}")

    # 2. Try OpenAI if API key is provided
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and not openai_key.startswith("your-"):
        try:
            from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
            _embedding_instance = OpenAIEmbeddingFunction(
                api_key=openai_key,
                model_name="text-embedding-3-small"
            )
            logger.info("[Embeddings] Initialized OpenAIEmbeddingFunction.")
            return _embedding_instance
        except Exception as e:
            logger.warning(f"[Embeddings] Failed to initialize OpenAIEmbeddingFunction: {e}")

    # 3. Default fallback provided by chromadb
    try:
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        _embedding_instance = DefaultEmbeddingFunction()
        logger.info("[Embeddings] Initialized Chroma DefaultEmbeddingFunction.")
        return _embedding_instance
    except Exception as e:
        logger.error(f"[Embeddings] Could not initialize any embedding function: {e}")
        return None
