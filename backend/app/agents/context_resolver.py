"""Context Resolver analyzing user intent, reference resolution, and task requirements using LLM."""

import json
from typing import Any, Dict, Optional
from backend.app.llm.llm_client import LLMClient

async def resolve_context(
    user_message: str,
    history: str,
    active_artifact: Optional[Dict[str, Any]] = None,
    llm_client: Optional[LLMClient] = None
) -> Dict[str, Any]:
    """
    Analyzes user message and active artifact / history context to resolve references using LLM.
    Supports entity reference resolution ("What about manager approval?") and PDF exports.
    """
    msg_lower = user_message.lower().strip()

    # Fast-paths for specific intents that do not require LLM resolution for task_type
    task_type = "general_conversation"
    empty_artifact_error = False

    is_pdf_intent = any(p in msg_lower for p in ["pdf", "download", "export"]) and (
        "create pdf" in msg_lower or "make pdf" in msg_lower or "download it" in msg_lower or "make it pdf" in msg_lower
    )
    
    if is_pdf_intent:
        if active_artifact:
            return {
                "original_query": user_message,
                "resolved_query": f"Convert active artifact '{active_artifact.get('title', 'document')}' to PDF",
                "task_type": "pdf_conversion",
            }
        elif history and len(history.strip()) > 15:
            return {
                "original_query": user_message,
                "resolved_query": "Convert previous assistant answer to PDF",
                "task_type": "pdf_conversion",
            }
        else:
            return {
                "original_query": user_message,
                "resolved_query": user_message,
                "task_type": "pdf_conversion",
                "empty_artifact_error": True,
            }

    if "leave letter" in msg_lower or "leave request" in msg_lower:
        return {
            "original_query": user_message,
            "resolved_query": user_message,
            "task_type": "leave_letter",
        }

    if "report" in msg_lower or "500 words" in msg_lower:
        return {
            "original_query": user_message,
            "resolved_query": user_message,
            "task_type": "report",
        }

    if is_modification_intent := any(p in msg_lower for p in ["shorter", "rewrite it", "modify it", "change date", "change the date"]):
        if active_artifact or (history and len(history.strip()) > 15):
            return {
                "original_query": user_message,
                "resolved_query": f"Modify previous content: {user_message}",
                "task_type": "artifact_modification",
            }

    # LLM Context Resolution
    resolved_query = user_message
    if history and llm_client:
        prompt = (
            "You are a Context Resolution Agent. Your task is to rewrite the user's latest query so it is fully standalone, "
            "incorporating any missing context from the conversation history.\n\n"
            "If the user says 'What about manager approval?' and the history discusses 'remote work policy', "
            "you should rewrite it to 'What about manager approval for the remote work policy?'.\n\n"
            "If the query is already self-contained or does not reference the history, return it exactly as is.\n\n"
            f"Conversation History:\n{history}\n\n"
            f"User's Latest Query: {user_message}\n\n"
            "Return ONLY a JSON object: {\"resolved_query\": \"<standalone_query>\"}"
        )
        try:
            decision_text = await llm_client.generate(prompt)
            cleaned_json = decision_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned_json)
            resolved_query = data.get("resolved_query", user_message)
        except Exception:
            resolved_query = user_message

    return {
        "original_query": user_message,
        "resolved_query": resolved_query,
        "task_type": task_type,
    }
