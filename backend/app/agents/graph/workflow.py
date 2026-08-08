from typing import Any, Dict
from langgraph.graph import END, START, StateGraph

from backend.app.agents.graph.state import GraphState
from backend.app.agents.graph.nodes.critic import critic_node
from backend.app.agents.graph.nodes.rag import rag_node
from backend.app.agents.graph.nodes.refine import refine_node
from backend.app.agents.graph.nodes.sql import sql_node
from backend.app.agents.graph.nodes.supervisor import supervisor_node
from backend.app.llm.llm_client import LLMClient
from backend.app.tools.web_search import search_web

MAX_REFLECTION_ATTEMPTS = 1


def create_workflow(llm_client: LLMClient):
    """Build the multi-agent supervisor workflow with Reflection and Critic evaluation."""

    async def supervisor(state: GraphState) -> Dict[str, Any]:
        return await supervisor_node(state, llm_client)

    async def sql_agent(state: GraphState) -> Dict[str, Any]:
        return await sql_node(state, llm_client)

    async def llm_node(state: GraphState) -> Dict[str, Any]:
        web_results = state.get("web_results")
        rag_context = state.get("rag_context")
        sql_result = state.get("sql_result")
        history = state.get("history")

        history_prefix = f"Prior Conversation History:\n{history}\n\n" if history else ""

        if web_results:
            prompt = (
                f"{history_prefix}"
                "Answer the user's question concisely using the web search results below. "
                "Use only information supported by the results.\n\n"
                f"User question: {state['user_message']}\n\n"
                f"Web search results:\n{web_results}"
            )
        elif rag_context:
            prompt = (
                f"{history_prefix}"
                "Answer the user's question concisely using the retrieved enterprise context below. "
                "Use only information supported by the context.\n\n"
                f"User question: {state['user_message']}\n\n"
                f"Retrieved enterprise context:\n{rag_context}"
            )
        elif sql_result:
            prompt = (
                f"{history_prefix}"
                "Answer the user's question concisely using the database query results below. "
                "Use only information supported by the database query results.\n\n"
                f"User question: {state['user_message']}\n\n"
                f"Database query results:\n{sql_result}"
            )
        else:
            prompt = (
                f"{history_prefix}"
                f"User question: {state['user_message']}"
            )
        response = await llm_client.generate(prompt)
        return {"draft_response": response}

    async def web_node(state: GraphState) -> Dict[str, Any]:
        return {"web_results": search_web(state["user_message"])}

    async def critic(state: GraphState) -> Dict[str, Any]:
        return await critic_node(state, llm_client)

    async def refine(state: GraphState) -> Dict[str, Any]:
        return await refine_node(state, llm_client)

    async def final_response_node(state: GraphState) -> Dict[str, Any]:
        return {"final_response": state.get("draft_response", "")}

    def route_after_critic(state: GraphState) -> str:
        approved = state.get("critic_approved", True)
        count = state.get("reflection_count", 0)
        if not approved and count < MAX_REFLECTION_ATTEMPTS:
            return "refine_node"
        return "final_response_node"

    graph = StateGraph(GraphState)
    graph.add_node("supervisor", supervisor)
    graph.add_node("rag_node", rag_node)
    graph.add_node("sql_node", sql_agent)
    graph.add_node("web_node", web_node)
    graph.add_node("llm_node", llm_node)
    graph.add_node("critic_node", critic)
    graph.add_node("refine_node", refine)
    graph.add_node("final_response_node", final_response_node)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lambda state: state["route"],
        {"direct": "llm_node", "rag": "rag_node", "web": "web_node", "sql": "sql_node"},
    )
    graph.add_edge("rag_node", "llm_node")
    graph.add_edge("web_node", "llm_node")
    graph.add_edge("sql_node", "llm_node")
    graph.add_edge("llm_node", "critic_node")

    graph.add_conditional_edges(
        "critic_node",
        route_after_critic,
        {"refine_node": "refine_node", "final_response_node": "final_response_node"},
    )

    graph.add_edge("refine_node", "final_response_node")
    graph.add_edge("final_response_node", END)

    return graph.compile()
