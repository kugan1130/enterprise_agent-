from typing import Literal, NotRequired, TypedDict


class GraphState(TypedDict):
    """Data passed through the minimal chat workflow."""

    user_message: str
    session_id: NotRequired[str]
    history: NotRequired[str]
    route: NotRequired[Literal["direct", "rag", "web", "sql", "research"]]
    guardrail_allowed: NotRequired[bool]
    guardrail_reason: NotRequired[str]
    tool_permitted: NotRequired[bool]
    requires_approval: NotRequired[bool]
    human_approved: NotRequired[bool]
    rag_context: NotRequired[str]
    web_results: NotRequired[str]
    sql_result: NotRequired[str]
    research_plan: NotRequired[list[dict[str, str]]]
    research_results: NotRequired[list[dict[str, Any]]]
    report_output: NotRequired[str]
    draft_response: NotRequired[str]
    critic_approved: NotRequired[bool]
    critic_reason: NotRequired[str]
    critic_suggestions: NotRequired[str]
    reflection_count: NotRequired[int]
    final_response: NotRequired[str]
