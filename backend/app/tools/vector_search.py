import logging
from typing import Any, Dict, List
from langchain_core.tools import tool

from backend.app.rag.retriever import retrieve_documents

logger = logging.getLogger("enterprise_ai.vector_search")


@tool
def search_documents(query: str, limit: int = 4) -> List[Dict[str, Any]]:
    """Search uploaded enterprise documents (PDFs, policies, specs, guides) for relevant context passages.
    
    Args:
        query: The user question or search topic.
        limit: Number of top document chunks to retrieve (default 4).
    """
    return retrieve_documents(query=query, limit=limit)
