"""Request-routing node for the chat workflow."""

from typing import Literal

from pydantic import BaseModel

from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient


class RoutingDecision(BaseModel):
    """Structured decision returned by the supervisor."""

    route: Literal["direct", "rag", "web", "sql"]


async def supervisor_node(state: GraphState, llm_client: LLMClient) -> dict[str, str]:
    """Classify a request as a direct, RAG, web, or SQL request."""
    decision_text = await llm_client.generate(
        "Classify the user request into one route: 'direct', 'rag', 'web', or 'sql'. "
        "Use 'sql' for database queries, table statistics, or sales data questions. "
        "Use 'rag' for questions about enterprise documents or company policy. "
        "Use 'web' only when current external information or web search is needed. "
        "Return only valid JSON in this exact shape: {\"route\": \"direct\"}.\n\n"
        f"User request: {state['user_message']}"
    )
    decision = RoutingDecision.model_validate_json(decision_text)
    return {"route": decision.route}
