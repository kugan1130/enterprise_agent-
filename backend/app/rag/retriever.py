"""Semantic retrieval from the persistent enterprise document collection."""

from pathlib import Path
from typing import Any

import chromadb

from backend.app.rag.embeddings import embed_query
from backend.app.rag.ingest import COLLECTION_NAME, DEFAULT_CHROMA_PATH


def retrieve(
    query: str,
    *,
    limit: int = 4,
    persist_path: Path = DEFAULT_CHROMA_PATH,
    collection_name: str = COLLECTION_NAME,
) -> list[dict[str, Any]]:
    """Return the most semantically relevant indexed chunks for a query."""
    client = chromadb.PersistentClient(path=str(persist_path))
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    matches = collection.query(
        query_embeddings=[embed_query(query)],
        n_results=limit,
        include=["documents", "metadatas", "distances"],
    )
    documents = matches["documents"] or [[]]
    metadatas = matches["metadatas"] or [[]]
    distances = matches["distances"] or [[]]

    return [
        {
            "text": document,
            "metadata": metadata,
            "distance": distance,
        }
        for document, metadata, distance in zip(
            documents[0],
            metadatas[0],
            distances[0],
            strict=True,
        )
    ]
