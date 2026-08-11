"""Semantic retrieval tool wrapped as a standard LangChain Tool for vector store access."""

import logging
from pathlib import Path
from typing import Any, List, Dict
import chromadb

from backend.app.rag.embeddings import embed_query
from backend.app.rag.ingest import COLLECTION_NAME, DEFAULT_CHROMA_PATH

logger = logging.getLogger("enterprise_ai.rag_retriever")
MAX_COSINE_DISTANCE = 0.95


def retrieve_documents(
    query: str,
    limit: int = 4,
    user_id: Any = None,
) -> List[Dict[str, Any]]:
    """Retrieves semantically relevant document chunks directly from ChromaDB vector collection."""
    try:
        from backend.app.core.chroma import get_chroma_client
        client = get_chroma_client()
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        query_kwargs: Dict[str, Any] = {
            "query_embeddings": [embed_query(query)],
            "n_results": limit,
            "include": ["documents", "metadatas", "distances"],
        }

        if user_id is not None:
            uid_val = int(user_id)
            query_kwargs["where"] = {"$or": [{"user_id": uid_val}, {"user_id": 0}]}

        try:
            matches = collection.query(**query_kwargs)
        except Exception:
            # Fallback without where filter if where operator fails or collection schemas vary
            query_kwargs.pop("where", None)
            matches = collection.query(**query_kwargs)

        documents = matches.get("documents", [[]])
        metadatas = matches.get("metadatas", [[]])
        distances = matches.get("distances", [[]])

        # If Chroma returns None for these (happens when empty)
        documents = documents or [[]]
        metadatas = metadatas or [[]]
        distances = distances or [[]]

        results = [
            {
                "text": document,
                "metadata": metadata,
                "distance": distance,
            }
            for document, metadata, distance in zip(
                documents[0],
                metadatas[0],
                distances[0],
                strict=False,
            )
            if distance <= MAX_COSINE_DISTANCE
        ]

        # Post-filter strictly for user isolation if user_id was provided
        if user_id is not None:
            target_uid = int(user_id)
            results = [
                r for r in results
                if r.get("metadata", {}).get("user_id") is None
                or r.get("metadata", {}).get("user_id") == target_uid
                or r.get("metadata", {}).get("user_id") == 0
            ]

        sources = [r.get("metadata", {}).get("filename") or "doc.pdf" for r in results]
        
        # Add Detailed Diagnostic Logging as requested
        logger.info("=== RAG DIAGNOSTIC LOG ===")
        logger.info(f"Query: {query}")
        logger.info(f"Collection: {COLLECTION_NAME}")
        logger.info(f"Top K requested: {limit}")
        logger.info(f"Similarity Threshold: {MAX_COSINE_DISTANCE}")
        logger.info(f"User ID filter: {user_id}")
        logger.info(f"Results returned: {len(results)}")
        logger.info(f"Retrieved Document IDs: {[r.get('metadata', {}).get('document_id') for r in results]}")
        logger.info(f"Retrieved Filenames: {sources}")
        logger.info("==========================")
        
        return results

    except Exception as err:
        logger.error("RAG DIAGNOSTIC ERROR: query=%r error=%s", query, err)
        return [{"text": f"Retrieval error: {str(err)}", "metadata": {}, "distance": 1.0}]


def retrieve(
    query: str,
    limit: int = 4,
    user_id: Any = None,
) -> List[Dict[str, Any]]:
    """Retrieves semantically relevant document chunks from the enterprise vector store."""
    return retrieve_documents(query, limit, user_id=user_id)
