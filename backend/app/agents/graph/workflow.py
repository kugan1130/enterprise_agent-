from langgraph.graph import END, START, StateGraph

from backend.app.agents.graph.state import GraphState
from backend.app.agents.graph.nodes.supervisor import supervisor_node
from backend.app.llm.llm_client import LLMClient


def create_workflow(llm_client: LLMClient):
    """Build the single-node LLM workflow."""

    async def supervisor(state: GraphState) -> dict[str, str]:
        return await supervisor_node(state, llm_client)

    async def llm_node(state: GraphState) -> dict[str, str]:
        response = await llm_client.generate(state["user_message"])
        return {"final_response": response}

    async def web_node(state: GraphState) -> dict[str, str]:
        return {"final_response": "Web search route selected"}

    graph = StateGraph(GraphState)
    graph.add_node("supervisor", supervisor)
    graph.add_node("llm_node", llm_node)
    graph.add_node("web_node", web_node)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lambda state: state["route"],
        {"direct": "llm_node", "web": "web_node"},
    )
    graph.add_edge("llm_node", END)
    graph.add_edge("web_node", END)

    return graph.compile()
