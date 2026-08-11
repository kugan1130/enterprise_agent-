import logging
from typing import Any, Dict
from backend.app.agents.graph.state import AgentState
from backend.app.rag.retriever import retrieve_documents

logger = logging.getLogger("enterprise_ai.rag_agent")


async def rag_node(state: AgentState) -> Dict[str, Any]:
    """Executes similarity vector search against ChromaDB with user_id isolation."""
    query = str(state.get("current_query") or (state["messages"][-1].content if state.get("messages") else ""))
    user_id = state.get("user_id")
    try:
        results = retrieve_documents(query=query, limit=4, user_id=user_id)
        return {"rag_results": results}
    except Exception as err:
        logger.error("RAG Agent error: %s", err)
        return {"rag_results": [], "error": f"RAG Error: {err}"}
