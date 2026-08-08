"""Input guardrail validation node."""

from typing import Any, Dict
from backend.app.agents.graph.state import GraphState


def input_guardrail_node(state: GraphState) -> Dict[str, Any]:
    """Validates user input for malicious or destructive commands."""
    user_msg = state.get("user_message", "").lower()
    prohibited_keywords = ["drop database", "drop table", "truncate table", "rm -rf", "format c:"]
    
    for word in prohibited_keywords:
        if word in user_msg:
            return {
                "guardrail_allowed": False,
                "guardrail_reason": f"Prohibited operation keyword '{word}' detected.",
            }
            
    return {"guardrail_allowed": True}
