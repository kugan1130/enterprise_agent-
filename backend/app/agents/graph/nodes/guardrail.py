"""Input guardrail validation node."""

import re
from typing import Any, Dict

from backend.app.agents.graph.state import GraphState

MAX_INPUT_LENGTH = 2000

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?safety\s+rules",
    r"override\s+system\s+prompt",
    r"system\s+prompt:",
    r"bypass\s+security",
    r"you\s+are\n+now\s+unrestricted",
    r"jailbreak",
]


def input_guardrail_node(state: GraphState) -> Dict[str, Any]:
    """
    Validates incoming user message before routing to Supervisor or invoking LLM.

    Returns:
        Dict with keys:
            - guardrail_allowed (bool)
            - guardrail_reason (str)
    """
    user_message = state.get("user_message", "")

    if not user_message or not isinstance(user_message, str) or not user_message.strip():
        return {
            "guardrail_allowed": False,
            "guardrail_reason": "Request cannot be empty.",
        }

    cleaned_msg = user_message.strip()

    if len(cleaned_msg) > MAX_INPUT_LENGTH:
        return {
            "guardrail_allowed": False,
            "guardrail_reason": f"Input length exceeds maximum allowed limit of {MAX_INPUT_LENGTH} characters.",
        }

    lower_msg = cleaned_msg.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, lower_msg):
            return {
                "guardrail_allowed": False,
                "guardrail_reason": "Security guardrail flagged request for prompt injection patterns.",
            }

    return {
        "guardrail_allowed": True,
        "guardrail_reason": "Input passed security guardrails.",
    }
