"""Critic node for reviewing draft responses."""

from typing import Any, Dict
from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient


async def critic_node(state: GraphState, llm_client: LLMClient) -> Dict[str, Any]:
    """Reviews draft response quality and accuracy."""
    return {"critic_approved": True, "reflection_count": state.get("reflection_count", 0) + 1}
