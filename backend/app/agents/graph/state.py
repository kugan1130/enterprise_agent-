from typing import Literal, NotRequired, TypedDict


class GraphState(TypedDict):
    """Data passed through the minimal chat workflow."""

    user_message: str
    route: NotRequired[Literal["direct", "rag", "web", "sql"]]
    rag_context: NotRequired[str]
    web_results: NotRequired[str]
    sql_result: NotRequired[str]
    final_response: NotRequired[str]
