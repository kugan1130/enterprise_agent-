"""Human approval evaluation node."""

from typing import Any, Dict

from backend.app.agents.graph.state import GraphState

HIGH_IMPACT_KEYWORDS = {
    "delete",
    "drop",
    "truncate",
    "update",
    "alter",
    "grant",
    "revoke",
    "shutdown",
    "format",
}


def approval_check_node(state: GraphState) -> Dict[str, Any]:
    """
    Evaluates if a request contains high-impact or sensitive operations
    requiring explicit human approval.

    Returns:
        Dict with keys:
            - requires_approval (bool)
            - human_approved (Optional[bool])
    """
    user_message = state.get("user_message", "").lower()
    human_approved = state.get("human_approved")

    # Check if request targets high-impact or destructive operations
    words = set(user_message.split())
    has_high_impact = bool(words.intersection(HIGH_IMPACT_KEYWORDS))

    if not has_high_impact:
        return {
            "requires_approval": False,
            "human_approved": True,
        }

    # If high-impact operation detected, human approval is required
    return {
        "requires_approval": True,
        "human_approved": human_approved,
    }
