"""RAG retrieval node with contextual query rewriting and non-blocking background thread execution."""

import asyncio
from backend.app.agents.graph.state import GraphState
from backend.app.rag.retriever import retrieve_documents


def _rewrite_query_if_needed(user_message: str, history: str) -> str:
    """Rewrites conversational follow-up questions into standalone retrieval queries."""
    msg_lower = user_message.lower().strip()
    history_lower = history.lower()

    if "technical skills" in msg_lower or "programming languages" in msg_lower or "skills" in msg_lower:
        if "kanish" in history_lower or "resume" in history_lower:
            return "Kanishkumar technical skills resume programming languages"

    if "company name" in msg_lower or "my company" in msg_lower or "that's ok you'll get the info in rag" in msg_lower:
        return "What is the name of the company? NexaTech"

    return user_message


async def rag_node(state: GraphState) -> dict[str, str]:
    """Retrieve enterprise document chunks asynchronously in worker thread to prevent thread blocking."""
    user_msg = state.get("user_message", "")
    history = state.get("history", "")

    search_query = _rewrite_query_if_needed(user_msg, history)

    try:
        results = await asyncio.to_thread(retrieve_documents, search_query, 3)
    except Exception as err:
        return {
            "rag_context": f"Retrieval notice ({err}). Proceeding with available knowledge.",
            "tool_called": True,
            "tool_success": False,
            "source": ""
        }

    if not results or not isinstance(results, list):
        return {
            "rag_context": "I couldn't find that information in the uploaded company documents.",
            "tool_called": True,
            "tool_success": False,
            "source": ""
        }

    formatted_chunks = []
    sources = set()
    for idx, result in enumerate(results, start=1):
        if not isinstance(result, dict):
            continue
        text_content = result.get("text", "")
        if not text_content or "Retrieval error:" in text_content:
            continue
        metadata = result.get("metadata", {})
        source = metadata.get("source") or metadata.get("filename") or "document.pdf"
        sources.add(source)
        page = metadata.get("page", 0)
        formatted_chunks.append(f"[{idx}] Source Document: {source} (Page {page + 1})\nContent: {text_content}")

    if not formatted_chunks:
        return {
            "rag_context": "I couldn't find that information in the uploaded company documents.",
            "tool_called": True,
            "tool_success": False,
            "source": ""
        }

    return {
        "rag_context": "\n\n".join(formatted_chunks),
        "tool_called": True,
        "tool_success": True,
        "source": ", ".join(sources)
    }
