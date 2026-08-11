"""Short-term session memory management with Redis and In-Memory fallback."""

import json
from typing import Any, Dict, List
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from backend.app.core.redis import get_redis_client

# In-memory dictionary fallback when Redis server is offline
_in_memory_store: Dict[str, List[Dict[str, str]]] = {}

INTERNAL_STATUS_PATTERNS = [
    "evaluating request routing supervisor",
    "executed pipeline:",
    "execution completed.",
    "guardrail notice",
]


def _is_internal_control_message(text: str) -> bool:
    """Detects whether text is an internal UI activity, control message, or SSE event."""
    if text is None or not isinstance(text, str):
        return True
    trimmed = text.strip()
    if not trimmed:
        return False
    if trimmed.startswith("data: {") or trimmed.startswith("event: "):
        return True
    t_lower = trimmed.lower()
    return any(pattern in t_lower for pattern in INTERNAL_STATUS_PATTERNS)


def get_conversation_history(session_id: str) -> List[Dict[str, str]]:
    """Retrieves clean conversation history for a given session ID."""
    r = get_redis_client()
    key = f"chat_session:{session_id}"

    if r:
        try:
            raw_history = r.lrange(key, 0, -1)
            history = []
            for item in raw_history:
                try:
                    turn = json.loads(item)
                    if not _is_internal_control_message(turn.get("user", "")) and not _is_internal_control_message(turn.get("assistant", "")):
                        history.append(turn)
                except Exception:
                    pass
            return history
        except Exception as err:
            print(f"Redis memory read notice ({err}), using internal memory store...")

    raw_list = _in_memory_store.get(session_id, [])
    return [t for t in raw_list if not _is_internal_control_message(t.get("user", "")) and not _is_internal_control_message(t.get("assistant", ""))]


def add_conversation_turn(session_id: str, prompt: str, response: str) -> None:
    """Appends clean user/assistant turn to session history, excluding internal control messages."""
    if not prompt or not response:
        return
    if _is_internal_control_message(prompt) or _is_internal_control_message(response):
        return

    r = get_redis_client()
    key = f"chat_session:{session_id}"
    turn = {"user": prompt.strip(), "assistant": response.strip()}

    if r:
        try:
            r.rpush(key, json.dumps(turn))
            r.expire(key, 86400)  # Expire session memory after 24 hours
            print(f"Saved turn to Redis key: {key}")
            return
        except Exception as err:
            print(f"Redis memory write notice ({err}), using internal memory store...")

    if session_id not in _in_memory_store:
        _in_memory_store[session_id] = []
    _in_memory_store[session_id].append(turn)


def format_history_as_text(history: List[Dict[str, str]], max_turns: int = 12) -> str:
    """Formats clean conversation turns as plain text context string for LLM prompts."""
    if not history:
        return ""

    formatted_turns = []
    for turn in history[-max_turns:]:
        user_msg = turn.get("user", "").strip()
        asst_msg = turn.get("assistant", "").strip()
        if user_msg and asst_msg:
            formatted_turns.append(f"User: {user_msg}\nAssistant: {asst_msg}")

    return "\n\n".join(formatted_turns)


def get_conversation_messages(session_id: str, max_turns: int = 10) -> List[BaseMessage]:
    """Retrieves conversation history as native LangChain BaseMessage primitives."""
    turns = get_conversation_history(session_id)
    messages: List[BaseMessage] = []
    for turn in turns[-max_turns:]:
        user_text = turn.get("user", "").strip()
        asst_text = turn.get("assistant", "").strip()
        if user_text:
            messages.append(HumanMessage(content=user_text))
        if asst_text:
            messages.append(AIMessage(content=asst_text))
    return messages


def build_focused_context(
    session_id: str,
    current_message: str,
    max_turns: int = 12,
) -> str:
    """Builds a focused context string for the LLM containing recent conversation."""
    history = get_conversation_history(session_id)
    history_text = format_history_as_text(history, max_turns=max_turns)
    return history_text
