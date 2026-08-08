from typing import Literal, NotRequired, TypedDict


class GraphState(TypedDict):
    """Data passed through the minimal chat workflow."""

    user_message: str
    session_id: NotRequired[str]
    history: NotRequired[str]
    route: NotRequired[Literal["direct", "rag", "web", "sql"]]
    rag_context: NotRequired[str]
    web_results: NotRequired[str]
    sql_result: NotRequired[str]
    draft_response: NotRequired[str]
    critic_approved: NotRequired[bool]
    critic_reason: NotRequired[str]
    critic_suggestions: NotRequired[str]
    reflection_count: NotRequired[int]
    final_response: NotRequired[str]
