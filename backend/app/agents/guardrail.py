"""Input guardrail validation node enforcing security policies."""

import logging
from typing import Any, Dict
from backend.app.agents.graph.state import AgentState

logger = logging.getLogger("enterprise_ai.guardrail")


def input_guardrail_node(state: AgentState) -> Dict[str, Any]:
    """Validates user input for malicious or destructive commands."""
    user_msg = (state.get("current_query") or "").lower()
    prohibited_keywords = [
        "drop database", "drop table", "truncate table", "rm -rf", "format c:",
        "delete the entire postgresql database", "delete all company records",
        "delete all documents", "delete the database", "delete database"
    ]
    
    for word in prohibited_keywords:
        if word in user_msg:
            msg = "Security Alert: Request rejected by Guardrail. Destructive or prohibited operations are strictly forbidden."
            logger.warning("Guardrail rejected message containing '%s'", word)
            return {
                "guardrail_allowed": False,
                "guardrail_reason": f"Prohibited operation keyword '{word}' detected.",
                "final_response": msg,
                "routes": ["conversation"],
            }
            
    return {"guardrail_allowed": True}
