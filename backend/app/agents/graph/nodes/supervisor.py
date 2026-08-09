"""Request-routing supervisor node integrating Context Resolver and Task Dispatcher."""

import json
import re
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

ENTERPRISE_RAG_KEYWORDS = {
    "policy", "company", "leave", "security", "remote work", "company name",
    "benefit", "benefits", "employee benefits", "architecture", "engineering architecture",
    "business report", "q4", "q4 business report",
    "kanish", "kanishkumar", "resume", "skills", "handbook", "document", "rules"
}

SQL_METRIC_KEYWORDS = ("sales", "revenue", "count", "metrics", "database", "table", "customers", "sold", "profit")

# Deterministic intent patterns for structured/database questions.
SQL_INTENT_PATTERNS = re.compile(
    r"(\bhow many\b.*\b(sold|sales|product|products|units|orders|employees)\b)"
    r"|(\bhow much\b.*\b(sold|sales|revenue|cost)\b)"
    r"|(\btotal (?:sales|revenue|amount|sold|units|orders|products?)\b)"
    r"|(\bwhat were the (?:total )?(?:sales|revenue|amounts?|values?)\b)"
    r"|(\bwhich product\b)"
    r"|(\bsold the most\b)"
    r"|(\btop (?:selling|sold) (?:product|products)?\b)"
    r"|(\b(?:products?|units?|items?)\s+sold\b)"
    r"|(\bnumber of (?:sales?|units?|orders?|products?|customers?|returns?)\b)"
    r"|(\bsum\s+of\b)"
    r"|(\baverage\s+sales\b)"
    r"|(\bwhat was the (?:total|overall|average) (?:sales|revenue|amount)\b)"
    r"|(\binsert\b.*\bsale\b)"
    r"|(\bbought\b.*\bproducts?\b)"
)

WEB_EXPLICIT_KEYWORDS = {"search online", "search the internet", "search web", "web search", "latest news", "current trends", "external"}

def _looks_like_database_question(message_lower: str) -> bool:
    """Detects structured-data questions that must hit the SQL tool."""
    return bool(SQL_INTENT_PATTERNS.search(message_lower))


async def supervisor_node(state: GraphState, llm_client: LLMClient) -> dict[str, Any]:
    """Classifies request into direct, rag, web, sql, task, research, or planner routes."""
    user_msg = state.get("user_message", "").strip()
    history = state.get("history", "")
    active_artifact = state.get("artifact")
    user_msg_lower = user_msg.lower().strip("!.,?")

    # 1. Fast-path for simple conversational greetings
    if user_msg_lower in GREETINGS_SET:
        return {"route": "direct", "task_type": "general_conversation"}

    # 2. CONTEXT RESOLVER: Resolve artifact references and follow-up intent
    context_res = resolve_context(user_msg, history, active_artifact)
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
    if any(kw in user_msg_lower for kw in WEB_EXPLICIT_KEYWORDS):
        return {"route": "web", "task_type": "web_research"}

    # 4. Fast-path for Enterprise RAG / Resume / Policy lookup
    if any(kw in user_msg_lower for kw in ENTERPRISE_RAG_KEYWORDS):
        return {"route": "rag", "task_type": "rag_question"}

    # 5. Check for Planner triggering (complex multi-agent queries)
    is_complex_analytical = ("sales" in user_msg_lower or "revenue" in user_msg_lower) and ("trend" in user_msg_lower or "news" in user_msg_lower or "ai" in user_msg_lower)
    if is_complex_analytical:
        return {"route": "planner", "task_type": "report"}

    # 6. Fast-path for SQL Analytics
    if any(kw in user_msg_lower for kw in SQL_METRIC_KEYWORDS) or _looks_like_database_question(user_msg_lower):
        return {"route": "sql", "task_type": "sql_question"}

    # 7. LLM Classification Fallback
    prompt = (
        "You are the Supervisor Agent of an Enterprise AI Assistant. "
        "Classify the request into the exact route:\n\n"
        "- 'direct': Simple greetings or general world knowledge.\n"
        "- 'rag': Questions about company policy, internal documents, uploaded resumes, or employees.\n"
        "- 'sql': Database queries, sales figures, revenue calculations.\n"
        "- 'web': Questions requiring live current internet search or external news.\n"
        "- 'task': Requests to write a leave letter, create a report, convert a document to PDF, or modify a document.\n"
        "- 'planner': Complex multi-step analytical requests combining sales database and live market trends.\n\n"
        f"Conversation History:\n{history}\n\n"
        f"User Request: {user_msg}\n\n"
        "Return ONLY JSON: {\"route\": \"<route_name>\"}"
    )

    try:
        decision_text = await llm_client.generate(prompt)
        cleaned_json = decision_text.replace("```json", "").replace("```", "").strip()
        decision = RoutingDecision.model_validate_json(cleaned_json)
        return {"route": decision.route, "task_type": task_type or "general_conversation"}
    except Exception:
        return {"route": "direct", "task_type": "general_conversation"}
