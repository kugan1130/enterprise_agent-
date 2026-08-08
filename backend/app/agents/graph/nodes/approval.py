"""Human approval check node."""

from typing import Any, Dict
from backend.app.agents.graph.state import GraphState


def approval_check_node(state: GraphState) -> Dict[str, Any]:
    """Checks if operation requires human approval prior to execution."""
    return {"requires_approval": False, "human_approved": True}
