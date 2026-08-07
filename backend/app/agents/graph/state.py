from typing import NotRequired, TypedDict


class GraphState(TypedDict):
    """Data passed through the minimal chat workflow."""

    user_message: str
    final_response: NotRequired[str]
