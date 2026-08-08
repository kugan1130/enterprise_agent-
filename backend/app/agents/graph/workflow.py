"""Multi-Agent LangGraph Workflow Specification."""

import json
from typing import Any, Dict
from langgraph.graph import END, START, StateGraph

from backend.app.agents.graph.state import GraphState
from backend.app.agents.graph.nodes.guardrail import input_guardrail_node
from backend.app.agents.graph.nodes.supervisor import supervisor_node
from backend.app.agents.graph.nodes.approval import approval_check_node
from backend.app.agents.graph.nodes.rag import rag_node
from backend.app.agents.graph.nodes.sql import sql_node
from backend.app.agents.graph.nodes.planner import planner_node
from backend.app.agents.graph.nodes.researcher import parallel_research_node
from backend.app.agents.graph.nodes.reporter import report_node
from backend.app.agents.graph.nodes.critic import critic_node
from backend.app.agents.graph.nodes.refine import refine_node
from backend.app.llm.llm_client import LLMClient
from backend.app.tools.web_search import search_web

MAX_REFLECTION_ATTEMPTS = 1


def create_workflow(llm_client: LLMClient):
    """Build the production multi-agent supervisor workflow."""

    async def guardrail(state: GraphState) -> Dict[str, Any]:
        return input_guardrail_node(state)

    async def supervisor(state: GraphState) -> Dict[str, Any]:
        return await supervisor_node(state, llm_client)

    async def approval(state: GraphState) -> Dict[str, Any]:
        return approval_check_node(state)

    async def sql_agent(state: GraphState) -> Dict[str, Any]:
        return await sql_node(state, llm_client)

    async def planner(state: GraphState) -> Dict[str, Any]:
        return await planner_node(state, llm_client)

    async def researcher(state: GraphState) -> Dict[str, Any]:
        return await parallel_research_node(state, llm_client)

    async def reporter(state: GraphState) -> Dict[str, Any]:
        return await report_node(state, llm_client)

    async def llm_node(state: GraphState) -> Dict[str, Any]:
        user_message = state.get("user_message", "")
        history = state.get("history", "")
        web_results = state.get("web_results")
        rag_context = state.get("rag_context")
        sql_result_raw = state.get("sql_result")

        history_prefix = f"Conversation History:\n{history}\n\n" if history else ""

        if web_results:
            prompt = (
                f"{history_prefix}"
                "Answer the user's question concisely using the web search results below. "
                "Include web source links when applicable.\n\n"
                f"User question: {user_message}\n\n"
                f"Web search results:\n{web_results}"
            )
        elif rag_context:
            prompt = (
                f"{history_prefix}"
                "Answer the user's question concisely using the retrieved enterprise context below. "
                "Include document filename sources when applicable. "
                "If the information is not present in the context, explicitly state that it was not found in the documents.\n\n"
                f"User question: {user_message}\n\n"
                f"Retrieved enterprise context:\n{rag_context}"
            )
        elif sql_result_raw:
            try:
                sql_data = json.loads(sql_result_raw)
                if not sql_data.get("success"):
                    err_msg = sql_data.get("error", "Query execution failed.")
                    return {
                        "draft_response": f"I couldn't execute the requested database query due to a schema or database error: {err_msg}. Please verify available table and column names."
                    }

                rows = sql_data.get("rows", [])
                if not rows:
                    prompt = (
                        f"{history_prefix}"
                        "The database query executed successfully, but returned 0 rows (empty dataset).\n"
                        "Inform the user concisely that no matching records were found in the database.\n\n"
                        f"User question: {user_message}"
                    )
                else:
                    prompt = (
                        f"{history_prefix}"
                        "Answer the user's question concisely using the successful database query results below. "
                        "Use only exact numbers, names, and metrics from the results without fabricating data.\n\n"
                        f"User question: {user_message}\n\n"
                        f"Database query results:\n{json.dumps(rows, indent=2)}"
                    )
            except Exception:
                prompt = (
                    f"{history_prefix}"
                    "Answer the user's question using the database query results below:\n\n"
                    f"User question: {user_message}\n\n"
                    f"Database results: {sql_result_raw}"
                )
        else:
            # Direct greeting, general query, or follow-up question
            prompt = (
                "You are an enterprise AI Assistant. "
                "Answer the user's question, greeting, or follow-up directly, concisely, and helpfully. "
                "If the user is asking a follow-up question (e.g., 'just give name only'), refer directly to the conversation history.\n\n"
                f"{history_prefix}"
                f"User: {user_message}"
            )

        response = await llm_client.generate(prompt)
        return {"draft_response": response}

    async def web_node(state: GraphState) -> Dict[str, Any]:
        return {"web_results": search_web(state.get("user_message", ""))}

    async def critic(state: GraphState) -> Dict[str, Any]:
        return await critic_node(state, llm_client)

    async def refine(state: GraphState) -> Dict[str, Any]:
        return await refine_node(state, llm_client)

    async def final_response_node(state: GraphState) -> Dict[str, Any]:
        if state.get("guardrail_allowed") is False:
            return {"final_response": f"Security Guardrail Notice: {state.get('guardrail_reason', 'Request blocked.')}"}
        if state.get("requires_approval") is True and state.get("human_approved") is not True:
            return {"final_response": "Action Paused: Human approval is required to execute sensitive or destructive operations."}
        return {"final_response": state.get("draft_response", "")}

    def route_after_guardrail(state: GraphState) -> str:
        if state.get("guardrail_allowed") is False:
            return "final_response_node"
        return "supervisor"

    def route_after_approval(state: GraphState) -> str:
        if state.get("requires_approval") is True and state.get("human_approved") is not True:
            return "final_response_node"
        return "sql_node"

    def route_after_critic(state: GraphState) -> str:
        approved = state.get("critic_approved", True)
        count = state.get("reflection_count", 0)
        if not approved and count < MAX_REFLECTION_ATTEMPTS:
            return "refine_node"
        return "final_response_node"

    graph = StateGraph(GraphState)
    graph.add_node("guardrail_node", guardrail)
    graph.add_node("supervisor", supervisor)
    graph.add_node("approval_node", approval)
    graph.add_node("rag_node", rag_node)
    graph.add_node("sql_node", sql_agent)
    graph.add_node("web_node", web_node)
    graph.add_node("planner_node", planner)
    graph.add_node("researcher_node", researcher)
    graph.add_node("reporter_node", reporter)
    graph.add_node("llm_node", llm_node)
    graph.add_node("critic_node", critic)
    graph.add_node("refine_node", refine)
    graph.add_node("final_response_node", final_response_node)

    graph.add_edge(START, "guardrail_node")

    graph.add_conditional_edges(
        "guardrail_node",
        route_after_guardrail,
        {"supervisor": "supervisor", "final_response_node": "final_response_node"},
    )

    graph.add_conditional_edges(
        "supervisor",
        lambda state: state.get("route", "direct"),
        {
            "direct": "llm_node",
            "rag": "rag_node",
            "web": "web_node",
            "sql": "approval_node",
            "research": "planner_node",
        },
    )

    graph.add_conditional_edges(
        "approval_node",
        route_after_approval,
        {"sql_node": "sql_node", "final_response_node": "final_response_node"},
    )

    graph.add_edge("rag_node", "llm_node")
    graph.add_edge("web_node", "llm_node")
    graph.add_edge("sql_node", "llm_node")
    graph.add_edge("planner_node", "researcher_node")
    graph.add_edge("researcher_node", "reporter_node")
    graph.add_edge("reporter_node", "critic_node")
    graph.add_edge("llm_node", "critic_node")

    graph.add_conditional_edges(
        "critic_node",
        route_after_critic,
        {"refine_node": "refine_node", "final_response_node": "final_response_node"},
    )

    graph.add_edge("refine_node", "final_response_node")
    graph.add_edge("final_response_node", END)

    return graph.compile()
