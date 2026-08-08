"""Planner node for complex research workflows."""

from typing import Any, Dict
from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient


async def planner_node(state: GraphState, llm_client: LLMClient) -> Dict[str, Any]:
    """Generates a structured research plan for deep research queries."""
    user_msg = state.get("user_message", "")
    return {
        "research_plan": [
            {"step": 1, "task": f"Analyze query parameters for '{user_msg}'"},
            {"step": 2, "task": "Search enterprise knowledge base and web findings."},
        ]
    }
