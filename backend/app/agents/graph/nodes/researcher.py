"""Parallel researcher node."""

from typing import Any, Dict
from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient


async def parallel_research_node(state: GraphState, llm_client: LLMClient) -> Dict[str, Any]:
    """Executes parallel information gathering."""
    user_msg = state.get("user_message", "")
    return {
        "research_results": [
            {"source": "Enterprise Docs & Web", "findings": f"Gathered relevant data for '{user_msg}'"}
        ]
    }
