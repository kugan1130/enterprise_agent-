from typing import Literal, NotRequired, TypedDict


class GraphState(TypedDict):
    """Data passed through the minimal chat workflow."""

    user_message: str
    route: NotRequired[Literal["direct", "web"]]
    final_response: NotRequired[str]
