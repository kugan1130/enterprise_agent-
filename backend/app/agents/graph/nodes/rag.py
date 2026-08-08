"""RAG retrieval node for the chat workflow."""

from backend.app.agents.graph.state import GraphState
from backend.app.rag.retriever import retrieve


def rag_node(state: GraphState) -> dict[str, str]:
    """Retrieve enterprise document chunks with explicit source citations for the user's question."""
    results = retrieve(state.get("user_message", ""))
    if not results:
        return {"rag_context": "No relevant enterprise documents were found for this query."}

    formatted_chunks = []
    for idx, result in enumerate(results, start=1):
        metadata = result.get("metadata", {})
        source = metadata.get("source") or metadata.get("filename") or "document.pdf"
        page = metadata.get("page", 0)
        formatted_chunks.append(f"[{idx}] Source Document: {source} (Page {page + 1})\nContent: {result['text']}")

    return {"rag_context": "\n\n".join(formatted_chunks)}
