"""Idempotent ChromaDB Seeder for Startup Frameworks and Case Studies.

Reads markdown documents from services/business_intelligence/data/seed/
and indexes them into a persistent ChromaDB collection.
"""

import os
import glob
import logging
from typing import List, Dict
from services.business_intelligence.app.rag.vector_store import (
    ChromaVectorStore,
    DEFAULT_PERSIST_DIRECTORY,
    DEFAULT_COLLECTION_NAME,
)

logger = logging.getLogger(__name__)

SEED_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "seed"
)


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> List[str]:
    """Splits text into overlapping token-approximated chunks."""
    words = text.split()
    chunks = []
    i = 0
    step = max(1, chunk_size - overlap)
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += step
    return chunks


def seed_chromadb_if_empty(
    persist_directory: str = DEFAULT_PERSIST_DIRECTORY,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    force_reseed: bool = False
) -> int:
    """Checks collection count; if 0 or uninitialized, seeds documents into ChromaDB.
    Returns total document chunks indexed.
    """
    store = ChromaVectorStore(
        persist_directory=persist_directory,
        collection_name=collection_name
    )

    try:
        current_count = store.count()
    except Exception as e:
        logger.error(f"[RAG Seeder] Failed to connect to vector store: {e}")
        return 0

    if current_count > 0 and not force_reseed:
        logger.info(f"[RAG Seeder] Collection '{collection_name}' already seeded with {current_count} chunks.")
        return current_count

    logger.info(f"[RAG Seeder] Seeding collection '{collection_name}' from {SEED_DIR}...")
    md_files = glob.glob(os.path.join(SEED_DIR, "*.md"))
    if not md_files:
        logger.warning(f"[RAG Seeder] No markdown files found in {SEED_DIR}.")
        return 0

    total_chunks = 0
    ids, documents, metadatas = [], [], []

    for file_path in md_files:
        filename = os.path.basename(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        file_chunks = chunk_text(content)
        for idx, chunk in enumerate(file_chunks):
            chunk_id = f"{filename}_{idx}"
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append({"source": filename, "chunk_index": idx})
            total_chunks += 1

    if ids:
        store.add_documents(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"[RAG Seeder] Successfully indexed {total_chunks} chunks into ChromaDB.")

    return store.count()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_chromadb_if_empty()
