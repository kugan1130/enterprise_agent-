"""Short-term conversation memory manager using Redis."""

import json
from typing import Any, Dict, List

from backend.app.core.config import settings
from backend.app.core.redis import get_redis_client

# In-memory fallback dictionary if Redis server is unreachable
_in_memory_store: Dict[str, List[Dict[str, str]]] = {}


def get_conversation_history(session_id: str) -> List[Dict[str, str]]:
    """
    Retrieve recent conversation history for a given session_id.

    Args:
        session_id: Unique session identifier.

    Returns:
        List of message dictionaries: [{"role": "user", "content": "..."}, ...]
    """
    if not session_id:
        session_id = "default_session"

    key = f"conversation:{session_id}"
    limit = settings.MAX_MEMORY_MESSAGES

    try:
        r = get_redis_client()
        # Fetch the last 'limit' messages from the Redis list
        raw_messages = r.lrange(key, -limit, -1)
        return [json.loads(m) for m in raw_messages]
    except Exception:
        # Fallback to local in-memory store if Redis is unavailable
        history = _in_memory_store.get(session_id, [])
        return history[-limit:]


def add_conversation_turn(session_id: str, user_message: str, assistant_message: str) -> None:
    """
    Append a user prompt and assistant response turn to the session history.

    Args:
        session_id: Unique session identifier.
        user_message: User's input text.
        assistant_message: Assistant's response text.
    """
    if not session_id:
        session_id = "default_session"

    key = f"conversation:{session_id}"
    limit = settings.MAX_MEMORY_MESSAGES

    user_turn = json.dumps({"role": "user", "content": user_message})
    assistant_turn = json.dumps({"role": "assistant", "content": assistant_message})

    try:
        r = get_redis_client()
        r.rpush(key, user_turn, assistant_turn)
        # Trim list to keep only the recent limit messages
        r.ltrim(key, -limit, -1)
    except Exception:
        # Fallback to local in-memory store
        if session_id not in _in_memory_store:
            _in_memory_store[session_id] = []
        _in_memory_store[session_id].append({"role": "user", "content": user_message})
        _in_memory_store[session_id].append({"role": "assistant", "content": assistant_message})
        _in_memory_store[session_id] = _in_memory_store[session_id][-limit:]


def format_history_as_text(history: List[Dict[str, str]]) -> str:
    """
    Format message turn dictionaries into a clean text snippet for LLM context.
    """
    if not history:
        return ""

    lines = []
    for msg in history:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)
