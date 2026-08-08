"""Refine node for improving draft responses based on critic suggestions."""

from typing import Any, Dict

from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient


async def refine_node(state: GraphState, llm_client: LLMClient) -> Dict[str, Any]:
    """
    Improves the draft response using suggestions from the Critic Agent
    and increments the reflection_count.
    """
    user_message = state.get("user_message", "")
    draft_response = state.get("draft_response", "")
    reason = state.get("critic_reason", "")
    suggestions = state.get("critic_suggestions", "")
    current_count = state.get("reflection_count", 0)

    rag_context = state.get("rag_context", "")
    sql_result = state.get("sql_result", "")
    web_results = state.get("web_results", "")

    context_str = ""
    if rag_context:
        context_str += f"\nRetrieved Enterprise Context:\n{rag_context}"
    if sql_result:
        context_str += f"\nDatabase Query Result:\n{sql_result}"
    if web_results:
        context_str += f"\nWeb Search Results:\n{web_results}"

    prompt = (
        "You are an expert Assistant improving a draft response based on Critic feedback.\n\n"
        f"User Question: {user_message}\n"
        f"{context_str}\n\n"
        f"Original Draft Response: {draft_response}\n"
        f"Critic Issue: {reason}\n"
        f"Critic Improvement Suggestions: {suggestions}\n\n"
        "Generate a revised, concise, accurate answer that addresses all critic suggestions."
    )

    improved_response = await llm_client.generate(prompt)

    return {
        "draft_response": improved_response,
        "reflection_count": current_count + 1,
    }
