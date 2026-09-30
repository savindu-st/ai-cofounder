"""ChromaDB Vector Store wrapper for Business Intelligence knowledge corpus.

Manages collection lifecycle, document indexing, and querying for startup frameworks.
"""

import os
import logging
from typing import List, Dict, Optional, Any
from services.business_intelligence.app.rag.embeddings import get_embedding_function

logger = logging.getLogger(__name__)

DEFAULT_PERSIST_DIRECTORY = os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chroma")
DEFAULT_COLLECTION_NAME = "startup_frameworks"


class ChromaVectorStore:
    """Wrapper around persistent ChromaDB client."""

    def __init__(
        self,
        persist_directory: str = DEFAULT_PERSIST_DIRECTORY,
        collection_name: str = DEFAULT_COLLECTION_NAME
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self._client = None
        self._collection = None

    def _get_client(self):
        if self._client is None:
            import chromadb
            os.makedirs(self.persist_directory, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_directory)
        return self._client

    def get_collection(self):
        """Retrieves or creates the collection with the configured embedding function."""
        if self._collection is None:
            client = self._get_client()
            embedding_fn = get_embedding_function()
            try:
                if embedding_fn:
                    self._collection = client.get_or_create_collection(
                        name=self.collection_name,
                        embedding_function=embedding_fn,
                        metadata={"hnsw:space": "cosine"}
                    )
                else:
                    self._collection = client.get_or_create_collection(
                        name=self.collection_name,
                        metadata={"hnsw:space": "cosine"}
                    )
            except Exception as e:
                if "Embedding function conflict" in str(e):
                    # Collection was created with default or different embedding function; reuse existing
                    logger.warning(f"[VectorStore] Embedding conflict on '{self.collection_name}'. Reconnecting to existing collection.")
                    self._collection = client.get_collection(name=self.collection_name)
                else:
                    raise
        return self._collection

    def add_documents(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """Adds documents to the collection."""
        if not ids or not documents:
            return 0
        collection = self.get_collection()
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        return len(ids)

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Queries the vector store for nearest document chunks."""
        collection = self.get_collection()
        count = collection.count()
        if count == 0:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        actual_n = min(n_results, count)
        kwargs: Dict[str, Any] = {
            "query_texts": [query_text],
            "n_results": actual_n
        }
        if where:
            kwargs["where"] = where

        return collection.query(**kwargs)

    def count(self) -> int:
        """Returns total documents indexed."""
        collection = self.get_collection()
        return collection.count()
