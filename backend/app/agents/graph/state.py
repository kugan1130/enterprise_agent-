from typing import Any, Literal, NotRequired, TypedDict


class GraphState(TypedDict):
    """Data passed through the minimal chat workflow."""

    user_message: str
    route: NotRequired[Literal["direct", "rag", "web", "sql"]]
    rag_context: NotRequired[str]
    web_results: NotRequired[str]
    sql_result: NotRequired[str]
    final_response: NotRequired[str]
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
