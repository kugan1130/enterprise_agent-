"""Refine node for polishing response output."""

from typing import Any, Dict
from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient


async def refine_node(state: GraphState, llm_client: LLMClient) -> Dict[str, Any]:
    """Refines response output based on critic suggestions."""
    draft = state.get("draft_response", "")
    return {"draft_response": draft}
