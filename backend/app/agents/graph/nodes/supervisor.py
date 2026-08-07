"""Request-routing node for the chat workflow."""

from typing import Literal

from pydantic import BaseModel

from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient


class RoutingDecision(BaseModel):
    """Structured decision returned by the supervisor."""

    route: Literal["direct", "web"]


async def supervisor_node(state: GraphState, llm_client: LLMClient) -> dict[str, str]:
    """Classify a request as a direct LLM request or a web-search request."""
    decision_text = await llm_client.generate(
        "Classify the user request into one route: 'direct' or 'web'. "
        "Use 'web' only when current information or web search is needed. "
        "Return only valid JSON in this exact shape: {\"route\": \"direct\"}.\n\n"
        f"User request: {state['user_message']}"
    )
    decision = RoutingDecision.model_validate_json(decision_text)
    return {"route": decision.route}
