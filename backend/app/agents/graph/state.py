"""Unified strongly typed LangGraph State Specification for Enterprise AI Assistant."""

from typing import Any, Dict, List, Literal, NotRequired, TypedDict


class GraphState(TypedDict):
    """Unified strongly typed state passed across all agent nodes and execution loops."""

    user_id: NotRequired[str]
    session_id: NotRequired[str]
    messages: NotRequired[List[Dict[str, Any]]]
    user_message: str
    history: NotRequired[str]

    route: NotRequired[Literal["direct", "rag", "web", "sql", "research", "task", "planner"]]
    task_type: NotRequired[
        Literal[
            "general_conversation",
            "rag_question",
            "sql_question",
            "web_research",
            "leave_letter",
            "report",
            "pdf_conversion",
            "artifact_modification",
        ]
    ]

    current_query: NotRequired[str]
    retrieved_documents: NotRequired[List[Dict[str, Any]]]
    sql_result: NotRequired[Dict[str, Any]]
    web_results: NotRequired[List[Dict[str, Any]]]
    agent_results: NotRequired[List[Dict[str, Any]]]
    sources: NotRequired[List[Dict[str, Any]]]

    artifact: NotRequired[Dict[str, Any]]
    artifact_history: NotRequired[List[Dict[str, Any]]]

    reflection_result: NotRequired[Dict[str, Any]]
    retry_count: NotRequired[int]

    final_answer: NotRequired[Dict[str, Any]]
    errors: NotRequired[List[str]]
    chart_data: NotRequired[Dict[str, Any]]
    
    # Tool Execution Metadata
    tool_called: NotRequired[bool]
    tool_success: NotRequired[bool]
    source: NotRequired[str]

    # Retained backward-compatible fields
    rag_context: NotRequired[str]
    draft_response: NotRequired[str]
    human_approved: NotRequired[bool]
    guardrail_allowed: NotRequired[bool]
    guardrail_reason: NotRequired[str]
    critic_approved: NotRequired[bool]
    reflection_count: NotRequired[int]
    final_response: NotRequired[str]
