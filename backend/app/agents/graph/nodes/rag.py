"""RAG retrieval node for the chat workflow."""

from backend.app.agents.graph.state import GraphState
from backend.app.rag.retriever import retrieve


def rag_node(state: GraphState) -> dict[str, str]:
    """Retrieve enterprise document chunks for the user's original question."""
    results = retrieve(state["user_message"])
    context = "\n\n".join(
        f"Source: {result['metadata']['source']}\n{result['text']}" for result in results
    )
    return {"rag_context": context or "No relevant enterprise documents were found."}
