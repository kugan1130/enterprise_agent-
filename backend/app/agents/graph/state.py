from typing import Any, Dict, List, Optional, TypedDict
from langchain_core.messages import BaseMessage


class AgentState(TypedDict, total=False):
    """Clean TypedDict state passed across LangGraph nodes."""

    messages: List[BaseMessage]
    session_id: str
    user_id: Optional[str]
    current_query: str
    routes: List[str]  # e.g., ["conversation"], ["rag"], ["web"], ["sql"], or ["rag", "web"]

    web_results: List[str]
    rag_results: List[Dict[str, Any]]
    sql_results: List[Dict[str, Any]]

    final_response: Optional[str]
    error: Optional[str]
    artifact: Optional[Dict[str, Any]]
