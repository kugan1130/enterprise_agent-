from langgraph.graph import END, START, StateGraph

from backend.app.agents.graph.state import GraphState
from backend.app.agents.graph.nodes.rag import rag_node
from backend.app.agents.graph.nodes.sql import sql_node
from backend.app.agents.graph.nodes.supervisor import supervisor_node
from backend.app.llm.llm_client import LLMClient
from backend.app.tools.web_search import search_web


def create_workflow(llm_client: LLMClient):
    """Build the multi-agent supervisor workflow."""

    async def supervisor(state: GraphState) -> dict[str, str]:
        return await supervisor_node(state, llm_client)

    async def sql_agent(state: GraphState) -> dict[str, str]:
        return await sql_node(state, llm_client)

    async def llm_node(state: GraphState) -> dict[str, str]:
        web_results = state.get("web_results")
        prompt = state["user_message"]
        if web_results:
            prompt = (
                "Answer the user's question concisely using the web search results below. "
                "Use only information supported by the results.\n\n"
                f"User question: {state['user_message']}\n\n"
                f"Web search results:\n{web_results}"
            )
        elif rag_context := state.get("rag_context"):
            prompt = (
                "Answer the user's question concisely using the retrieved enterprise context below. "
                "Use only information supported by the context.\n\n"
                f"User question: {state['user_message']}\n\n"
                f"Retrieved enterprise context:\n{rag_context}"
            )
        elif sql_result := state.get("sql_result"):
            prompt = (
                "Answer the user's question concisely using the database query results below. "
                "Use only information supported by the database query results.\n\n"
                f"User question: {state['user_message']}\n\n"
                f"Database query results:\n{sql_result}"
            )
        response = await llm_client.generate(prompt)
        return {"final_response": response}

    async def web_node(state: GraphState) -> dict[str, str]:
        return {"web_results": search_web(state["user_message"])}

    graph = StateGraph(GraphState)
    graph.add_node("supervisor", supervisor)
    graph.add_node("rag_node", rag_node)
    graph.add_node("sql_node", sql_agent)
    graph.add_node("llm_node", llm_node)
    graph.add_node("web_node", web_node)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lambda state: state["route"],
        {"direct": "llm_node", "rag": "rag_node", "web": "web_node", "sql": "sql_node"},
    )
    graph.add_edge("rag_node", "llm_node")
    graph.add_edge("web_node", "llm_node")
    graph.add_edge("sql_node", "llm_node")
    graph.add_edge("llm_node", END)

    return graph.compile()
