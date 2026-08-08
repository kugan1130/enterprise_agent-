"""Request-routing node for the chat workflow."""

from typing import Literal

from pydantic import BaseModel

from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient


class RoutingDecision(BaseModel):
    """Structured decision returned by the supervisor."""

    route: Literal["direct", "rag", "web", "sql", "research"]


async def supervisor_node(state: GraphState, llm_client: LLMClient) -> dict[str, str]:
    """Classify a request into: direct, rag, web, sql, or research."""
    decision_text = await llm_client.generate(
        "Classify the user request into exactly one route: 'direct', 'rag', 'web', 'sql', or 'research'.\n"
        "Guidance:\n"
        "- Use 'research' for complex, multi-step research requests, multi-source comparisons (e.g. comparing sales with AI trends or comparing internal policy with market trends), or deep report requests.\n"
        "- Use 'sql' for simple database queries or sales table questions.\n"
        "- Use 'rag' for simple questions about internal enterprise documents or policies.\n"
        "- Use 'web' only when current external web search is needed.\n"
        "- Use 'direct' for general conversational questions.\n"
        "Return only valid JSON in this exact shape: {\"route\": \"direct\"}.\n\n"
        f"User request: {state['user_message']}"
    )
    decision = RoutingDecision.model_validate_json(decision_text)
    return {"route": decision.route}
