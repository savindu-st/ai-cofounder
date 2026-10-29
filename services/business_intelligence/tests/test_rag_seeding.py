"""Unit tests for ChromaDB Vector Store, Embeddings, and Hybrid Retriever."""

import pytest
import os
import shutil
import tempfile

from services.business_intelligence.app.rag.vector_store import ChromaVectorStore
from services.business_intelligence.app.rag.retriever import HybridRetriever
from services.business_intelligence.app.rag.seed_vector_store import seed_chromadb_if_empty


@pytest.fixture(scope="module")
def temp_chroma_dir():
    temp_dir = tempfile.mkdtemp(prefix="test_chroma_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_vector_store_seed_and_query(temp_chroma_dir):
    store = ChromaVectorStore(
        persist_directory=temp_chroma_dir,
        collection_name="test_frameworks"
    )

    docs = [
        "Osterwalder Business Model Canvas: Key Partners, Key Activities, and Value Propositions.",
        "Ash Maurya Lean Canvas focuses on Problem, Solution, Early Adopters, and Unfair Advantage.",
        "Direct-to-consumer businesses thrive on strong return on ad spend (ROAS) and repeat purchases."
    ]
    ids = ["doc1", "doc2", "doc3"]
    metadatas = [
        {"source": "bmc.md", "chunk_index": 0},
        {"source": "lean.md", "chunk_index": 1},
        {"source": "d2c.md", "chunk_index": 2}
    ]

    added = store.add_documents(ids=ids, documents=docs, metadatas=metadatas)
    assert added == 3
    assert store.count() == 3

    # Query
    results = store.query("Lean Canvas Early Adopters", n_results=2)
    retrieved_docs = results["documents"][0]
    assert len(retrieved_docs) >= 1
    assert any("Ash Maurya" in d for d in retrieved_docs)


def test_hybrid_retriever_mmr(temp_chroma_dir):
    store = ChromaVectorStore(
        persist_directory=temp_chroma_dir,
        collection_name="test_frameworks"
    )
    retriever = HybridRetriever(vector_store=store)

    chunks = retriever.retrieve(
        query="business model canvas blocks",
        block_name="value_propositions",
        k=3,
        top_n=2
    )

    assert len(chunks) <= 2
    assert all(hasattr(c, "text") and hasattr(c, "score") for c in chunks)
    assert chunks[0].score >= 0.0


def test_seeding_real_directory(temp_chroma_dir):
    # Tests seeding from the actual services/business_intelligence/data/seed directory
    count = seed_chromadb_if_empty(
        persist_directory=temp_chroma_dir,
        collection_name="test_seed_corpus",
        force_reseed=True
    )
    assert count > 0

    # Idempotency check: running again without force should return the same count without duplicate insertions
    count_second = seed_chromadb_if_empty(
        persist_directory=temp_chroma_dir,
        collection_name="test_seed_corpus",
        force_reseed=False
    )
    assert count_second == count
