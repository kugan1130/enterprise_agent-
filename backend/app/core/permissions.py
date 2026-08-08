"""Deterministic tool permission policy engine."""

from typing import Any, Dict

# Permitted operation policies per tool
PERMITTED_POLICIES = {
    "rag": {"read", "retrieve"},
    "web": {"search"},
    "sql": {"select"},
}

# Explicitly denied operations
DENIED_POLICIES = {
    "sql": {"insert", "update", "delete", "drop", "alter", "create", "truncate", "grant", "revoke"},
}


def check_tool_permission(tool_name: str, operation: str) -> Dict[str, Any]:
    """
    Evaluates whether a requested tool operation is permitted by application policy.

    Args:
        tool_name: Name of tool ('rag', 'web', 'sql').
        operation: Requested operation string (e.g. 'select', 'insert', 'search').

    Returns:
        Dict[str, Any] containing:
            - permitted (bool): True if allowed, False if denied.
            - reason (str): Explanation if denied.
    """
    tool = tool_name.lower().strip()
    op = operation.lower().strip()

    # Check explicit denial list first
    if tool in DENIED_POLICIES and op in DENIED_POLICIES[tool]:
        return {
            "permitted": False,
            "reason": f"Tool permission policy denied operation '{op.upper()}' on tool '{tool}'. Only read-only operations are allowed.",
        }

    # Check allowed list
    if tool in PERMITTED_POLICIES and op in PERMITTED_POLICIES[tool]:
        return {
            "permitted": True,
            "reason": "Operation permitted by application policy.",
        }

    return {
        "permitted": False,
        "reason": f"Operation '{op}' is not authorized on tool '{tool}'.",
    }
