"""Request-routing supervisor node for multi-agent workflow."""

import json
from typing import Literal
from pydantic import BaseModel

from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient


class RoutingDecision(BaseModel):
    """Structured decision returned by the supervisor."""
    route: Literal["direct", "rag", "web", "sql", "research"]


GREETINGS_SET = {
    "hi", "hello", "hey", "good morning", "good afternoon",
    "good evening", "thanks", "thank you", "bye", "goodbye"
}


async def supervisor_node(state: GraphState, llm_client: LLMClient) -> dict[str, str]:
    """Classifies user request into direct, rag, web, sql, or research routes."""
    user_msg = state.get("user_message", "").strip()
    history = state.get("history", "")
    user_msg_lower = user_msg.lower().strip("!.,?")

    # Issue 2 Fix: Fast-path for simple conversational greetings
    if user_msg_lower in GREETINGS_SET:
        return {"route": "direct"}

    # Issue 1 Fix: Follow-up question context awareness
    followup_phrases = ["just give name only", "just the name", "explain more", "what about the previous", "that one"]
    if any(phrase in user_msg_lower for phrase in followup_phrases) and history:
        return {"route": "direct"}

    prompt = (
        "You are the Supervisor Agent of an Enterprise AI Assistant. "
        "Select the minimum required agent route for the user request:\n\n"
        "- 'direct': Simple greetings, general knowledge, follow-up questions, or direct answers.\n"
        "- 'rag': Questions about company policy, internal documents, uploaded PDFs, or HR.\n"
        "- 'sql': Database queries, sales metrics, revenue calculations, or row counts.\n"
        "- 'web': Questions requiring live current internet search or external news.\n"
        "- 'research': Requests to generate a comprehensive report, PDF report, or detailed comparison.\n\n"
        f"Conversation History:\n{history}\n\n"
        f"Current User Request: {user_msg}\n\n"
        "Return ONLY a JSON object: {\"route\": \"<route_name>\"}"
    )

    try:
        decision_text = await llm_client.generate(prompt)
        # Strip potential markdown wrapper
        cleaned_json = decision_text.replace("```json", "").replace("```", "").strip()
        decision = RoutingDecision.model_validate_json(cleaned_json)
        return {"route": decision.route}
    except Exception as err:
        print(f"Supervisor routing notice ({err}), defaulting to 'direct'...")
        return {"route": "direct"}
