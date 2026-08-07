from langgraph.graph import END, START, StateGraph

from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient


def create_workflow(llm_client: LLMClient):
    """Build the single-node LLM workflow."""

    async def llm_node(state: GraphState) -> dict[str, str]:
        response = await llm_client.generate(state["user_message"])
        return {"final_response": response}

    graph = StateGraph(GraphState)
    graph.add_node("llm_node", llm_node)
    graph.add_edge(START, "llm_node")
    graph.add_edge("llm_node", END)

    return graph.compile()
