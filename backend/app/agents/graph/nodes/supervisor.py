"""Request-routing supervisor node integrating Context Resolver and Task Dispatcher."""

import json
from typing import Any, Dict, Literal
from pydantic import BaseModel

from backend.app.agents.context_resolver import resolve_context
from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient

class RoutingDecision(BaseModel):
    """Structured decision returned by the supervisor."""
    route: Literal["direct", "rag", "web", "sql", "research", "task", "planner"]

GREETINGS_SET = {
    "hi", "hello", "hey", "good morning", "good afternoon",
    "good evening", "thanks", "thank you", "bye", "goodbye"
}

WEB_EXPLICIT_KEYWORDS = {"search online", "search the internet", "search web", "web search", "latest news", "current trends", "external", "latest information", "current information", "today's information"}

async def supervisor_node(state: GraphState, llm_client: LLMClient) -> dict[str, Any]:
    """Classifies request strictly into direct, rag, web, sql, task, research, or planner routes."""
    user_msg = state.get("user_message", "").strip()
    history = state.get("history", "")
    active_artifact = state.get("artifact")
    user_msg_lower = user_msg.lower().strip("!.,?")

    # 1. Fast-path for simple conversational greetings
    if user_msg_lower in GREETINGS_SET:
        return {"route": "direct", "task_type": "general_conversation"}

    # 2. CONTEXT RESOLVER: Resolve artifact references and follow-up intent
    context_res = await resolve_context(user_msg, history, active_artifact, llm_client)
    
    # Use the explicitly resolved query for subsequent LLM evaluations in the supervisor
    resolved_query = context_res.get("resolved_query", user_msg)
    if context_res.get("empty_artifact_error"):
        msg = "I don't have a previous document in this conversation to convert to PDF."
        return {
            "route": "direct",
            "task_type": "pdf_conversion",
            "draft_response": msg,
            "final_response": msg,
        }

    task_type = context_res.get("task_type")
    if task_type in ["pdf_conversion", "leave_letter", "artifact_modification"]:
        return {"route": "task", "task_type": task_type}

    # 3. Fast-path for Web Search (HIGHEST PRIORITY AFTER TASKS)
    # Explicit web requests must go to Web even if words like "how many" appear.
    if any(kw in user_msg_lower for kw in WEB_EXPLICIT_KEYWORDS):
        return {"route": "web", "task_type": "web_research"}

    # 4. Domain-based LLM Classification
    # Do NOT use simplistic rules like "how many" -> SQL.
    # The route must be based on source/domain, not generic words.
    prompt = (
        "You are the Supervisor Agent of an Enterprise AI Assistant. "
        "Classify the request into the exact route based strictly on the source/domain:\n\n"
        "- 'planner': Use if ONE user query requires multiple agents/sources (e.g., 'Tell me our remote policy, calculate Q4 revenue, and search online for latest AI news.').\n"
        "- 'rag': Use if the question concerns information contained in uploaded documents (e.g., policies, resumes, guides, roadmaps, reports, benefits, architecture documents, structured-data descriptions). Example: 'How many phases are in the Agentic AI Engineer roadmap?' MUST go to RAG, not SQL.\n"
        "- 'sql': Use if the question asks for exact structured company/database information (e.g., sales, revenue, customers, products, quantities, orders, employees, database records).\n"
        "- 'web': Use if requiring live current internet search (e.g. 'search online').\n"
        "- 'direct': Use if the answer is clearly available from conversation memory, or for simple conversational filler.\n\n"
        "DISAMBIGUATION RULE FOR RAG vs SQL:\n"
        "Determine whether the user wants 'document meaning' (RAG) or an 'exact database value' (SQL). "
        "If ambiguous, use context to decide. Never blindly map 'how many' to SQL; consider the subject matter (e.g. roadmap phases = RAG, products sold = SQL).\n\n"
        f"Conversation History:\n{history}\n\n"
        f"User Request: {resolved_query}\n\n"
        "Return ONLY valid JSON: {\"route\": \"<route_name>\"}"
    )

    try:
        decision_text = await llm_client.generate(prompt)
        cleaned_json = decision_text.replace("```json", "").replace("```", "").strip()
        decision = RoutingDecision.model_validate_json(cleaned_json)
        return {"route": decision.route, "task_type": task_type or "general_conversation", "current_query": resolved_query}
    except Exception:
        # Fallback only when appropriate
        return {"route": "direct", "task_type": "general_conversation", "current_query": resolved_query}
