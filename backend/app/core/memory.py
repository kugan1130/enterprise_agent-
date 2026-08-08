"""Short-term session memory management with Redis and In-Memory fallback."""

import json
from typing import Any, Dict, List

from backend.app.core.redis import get_redis_client

# In-memory dictionary fallback when Redis server is offline
_in_memory_store: Dict[str, List[Dict[str, str]]] = {}


def get_conversation_history(session_id: str) -> List[Dict[str, str]]:
    """Retrieves conversation history for a given session ID."""
    r = get_redis_client()
    key = f"chat_session:{session_id}"

    if r:
        try:
            raw_history = r.lrange(key, 0, -1)
            history = []
            for item in raw_history:
                try:
                    history.append(json.loads(item))
                except Exception:
                    pass
            return history
        except Exception as err:
            print(f"Redis memory read notice ({err}), using internal memory store...")

    return _in_memory_store.get(session_id, [])


def add_conversation_turn(session_id: str, prompt: str, response: str) -> None:
    """Appends a user/assistant turn to the session history."""
    r = get_redis_client()
    key = f"chat_session:{session_id}"
    turn = {"user": prompt, "assistant": response}

    if r:
        try:
            r.rpush(key, json.dumps(turn))
            r.expire(key, 86400)  # Expire session memory after 24 hours
            return
        except Exception as err:
            print(f"Redis memory write notice ({err}), using internal memory store...")

    if session_id not in _in_memory_store:
        _in_memory_store[session_id] = []
    _in_memory_store[session_id].append(turn)


def format_history_as_text(history: List[Dict[str, str]]) -> str:
    """Formats conversation turns as plain text context string for LLM prompts."""
    if not history:
        return ""

    formatted_turns = []
    for turn in history[-5:]:  # Keep last 5 turns for prompt context window
        user_msg = turn.get("user", "")
        asst_msg = turn.get("assistant", "")
        formatted_turns.append(f"User: {user_msg}\nAssistant: {asst_msg}")

    return "\n\n".join(formatted_turns)
