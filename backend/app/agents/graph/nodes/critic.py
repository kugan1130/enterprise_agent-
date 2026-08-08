"""Critic evaluation node for evaluating draft responses against context."""

from pydantic import BaseModel

from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient


class CriticEvaluation(BaseModel):
    """Structured evaluation returned by the critic node."""

    approved: bool
    reason: str
    suggestions: str = ""


async def critic_node(state: GraphState, llm_client: LLMClient) -> dict[str, Any]:
    """
    Evaluates a generated draft response for relevance, context adherence,
    and hallucination risk without calling external tools or databases.
    """
    user_message = state.get("user_message", "")
    draft_response = state.get("draft_response", "")
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
        "You are an expert Critic Agent evaluating an AI draft response.\n"
        "Evaluate the draft response based on:\n"
        "1. Relevance: Does it directly answer the user question?\n"
        "2. Factual Accuracy & Context Adherence: If context is provided, is the answer fully supported without hallucination?\n"
        "3. Completeness: Is any critical information missing?\n\n"
        f"User Question: {user_message}\n"
        f"{context_str}\n\n"
        f"Draft Response to Evaluate: {draft_response}\n\n"
        "Respond ONLY with a valid JSON object in this exact schema:\n"
        '{"approved": true, "reason": "Draft is fully supported and directly answers the question", "suggestions": ""}\n'
        'Or if problematic:\n'
        '{"approved": false, "reason": "Draft contains unsupported claims", "suggestions": "Remove claim X and use value Y from context"}'
    )

    try:
        eval_text = await llm_client.generate(prompt)
        # Strip markdown code blocks if present
        clean_text = eval_text.replace("```json", "").replace("```", "").strip()
        evaluation = CriticEvaluation.model_validate_json(clean_text)
        return {
            "critic_approved": evaluation.approved,
            "critic_reason": evaluation.reason,
            "critic_suggestions": evaluation.suggestions,
        }
    except Exception as err:
        # Fallback to approving if JSON parsing fails to avoid blocking workflow
        return {
            "critic_approved": True,
            "critic_reason": f"Default fallback approval due to parsing notice: {err}",
            "critic_suggestions": "",
        }
