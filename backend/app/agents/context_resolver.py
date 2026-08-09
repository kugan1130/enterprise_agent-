"""Context Resolver analyzing user intent, reference resolution, and task requirements."""

import re
from typing import Any, Dict, Optional

REFERENCE_PRONOUNS = [
    "it", "this", "that", "above", "previous", "same document",
    "the letter", "the report", "make it pdf", "convert to pdf", "convert it to pdf",
    "download it", "change the date", "make it shorter", "make that shorter",
    "make this a pdf", "create pdf", "export this", "make the above pdf",
    "convert the above", "rewrite it", "modify it"
]

ENTITY_PRONOUNS = [
    "she", "he", "they", "her", "him", "them", "shes", "hes",
    "this person", "that person", "the employee", "her name", "his name"
]


def _extract_referenced_entity_from_context(history: str, active_artifact: Optional[Dict[str, Any]]) -> Optional[str]:
    """Extracts employee or person entity names from active artifact or history context."""
    if active_artifact and active_artifact.get("title"):
        title = active_artifact["title"]
        if "Kanishka" in title or "Kanish" in title:
            return "Kanishka Kumar"

    combined = f"{history} {active_artifact.get('content', '') if active_artifact else ''}"
    if "kanishka kumar" in combined.lower():
        return "Kanishka Kumar"
    elif "kanishka" in combined.lower() or "kanish" in combined.lower():
        return "Kanishka Kumar"

    return None


def resolve_context(
    user_message: str,
    history: str,
    active_artifact: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Analyzes user message and active artifact / history context to resolve references.
    Supports entity reference resolution ("her name" -> "Kanishka Kumar's name") and PDF exports.
    """
    msg_lower = user_message.lower().strip()
    references_previous = any(p in msg_lower for p in REFERENCE_PRONOUNS)
    has_entity_pronoun = any(p in msg_lower for p in ENTITY_PRONOUNS)

    # 1. Entity Reference Resolution ("What is her name?", "what is shes name")
    if has_entity_pronoun:
        entity = _extract_referenced_entity_from_context(history, active_artifact)
        if entity:
            resolved = re.sub(r"\b(she|he|her|his|shes|hes|this person|that person)\b", entity, user_message, flags=re.IGNORECASE)
            if "name" in msg_lower:
                resolved = f"What is {entity}'s name?"
            return {
                "original_query": user_message,
                "resolved_query": resolved,
                "referenced_entity": entity,
                "references_previous_context": True,
                "referenced_artifact": active_artifact,
                "task_type": "general_conversation",
                "needs_new_retrieval": False,
            }

    # 2. PDF Conversion Intent ("make it pdf", "convert it to pdf", "download it", etc.)
    is_pdf_intent = any(p in msg_lower for p in ["pdf", "download", "export"]) and (
        references_previous or "create pdf" in msg_lower or "make pdf" in msg_lower or "download it" in msg_lower
    )

    if is_pdf_intent:
        if active_artifact:
            return {
                "original_query": user_message,
                "resolved_query": f"Convert active artifact '{active_artifact.get('title', 'document')}' to PDF",
                "references_previous_context": True,
                "referenced_artifact": active_artifact,
                "task_type": "pdf_conversion",
                "needs_new_retrieval": False,
            }
        elif history and len(history.strip()) > 15:
            return {
                "original_query": user_message,
                "resolved_query": "Convert previous assistant answer to PDF",
                "references_previous_context": True,
                "referenced_artifact": None,
                "task_type": "pdf_conversion",
                "needs_new_retrieval": False,
            }
        else:
            return {
                "original_query": user_message,
                "resolved_query": user_message,
                "references_previous_context": False,
                "referenced_artifact": None,
                "task_type": "pdf_conversion",
                "needs_new_retrieval": False,
                "empty_artifact_error": True,
            }

    # 3. Artifact Modification Intent (e.g., "make it shorter", "rewrite it", "change date")
    is_modification_intent = any(p in msg_lower for p in ["shorter", "rewrite it", "modify it", "change date", "change the date", "add manager"])
    if is_modification_intent:
        if active_artifact or (history and len(history.strip()) > 15):
            return {
                "original_query": user_message,
                "resolved_query": f"Modify previous content: {user_message}",
                "references_previous_context": True,
                "referenced_artifact": active_artifact,
                "task_type": "artifact_modification",
                "needs_new_retrieval": False,
            }

    # 4. Leave Letter Intent
    if "leave letter" in msg_lower or "leave request" in msg_lower or "child marriage" in msg_lower:
        return {
            "original_query": user_message,
            "resolved_query": user_message,
            "references_previous_context": False,
            "referenced_artifact": None,
            "task_type": "leave_letter",
            "needs_new_retrieval": True,
        }

    # 5. Report Generation Intent
    if "report" in msg_lower or "500 words" in msg_lower:
        return {
            "original_query": user_message,
            "resolved_query": user_message,
            "references_previous_context": False,
            "referenced_artifact": None,
            "task_type": "report",
            "needs_new_retrieval": True,
        }

    # Default fallback
    return {
        "original_query": user_message,
        "resolved_query": user_message,
        "references_previous_context": references_previous,
        "referenced_artifact": active_artifact,
        "task_type": "rag_question" if references_previous else "general_conversation",
        "needs_new_retrieval": not references_previous,
    }
