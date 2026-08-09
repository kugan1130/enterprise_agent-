"""Multi-Agent LangGraph Workflow Specification with Task, Reflection, Aggregation, and Final Answer Nodes."""

import json
from typing import Any, Dict
from langgraph.graph import END, START, StateGraph

from backend.app.agents.aggregation import aggregate_node
from backend.app.agents.final_answer import final_answer_node
from backend.app.agents.graph.nodes.approval import approval_check_node
from backend.app.agents.graph.nodes.guardrail import input_guardrail_node
from backend.app.agents.graph.nodes.rag import rag_node
from backend.app.agents.graph.nodes.reporter import report_node
from backend.app.agents.graph.nodes.researcher import parallel_research_node
from backend.app.agents.graph.nodes.sql import sql_node
from backend.app.agents.graph.nodes.supervisor import supervisor_node
from backend.app.agents.graph.state import GraphState
from backend.app.agents.planner import planner_node as structured_planner_node
from backend.app.agents.reflection import reflection_node
from backend.app.agents.task_dispatcher import dispatch_task
from backend.app.llm.llm_client import LLMClient
from backend.app.services.artifact_service import create_artifact, save_session_artifact
from backend.app.tools.web_search import search_web

MAX_REFLECTION_ATTEMPTS = 2


def create_workflow(llm_client: LLMClient):
    """Build the production multi-agent supervisor workflow."""

    async def guardrail(state: GraphState) -> Dict[str, Any]:
        return input_guardrail_node(state)

    async def supervisor(state: GraphState) -> Dict[str, Any]:
        return await supervisor_node(state, llm_client)

    async def approval(state: GraphState) -> Dict[str, Any]:
        return approval_check_node(state)

    async def rag(state: GraphState) -> Dict[str, Any]:
        return await rag_node(state)

    async def sql_agent(state: GraphState) -> Dict[str, Any]:
        return await sql_node(state, llm_client)

    async def planner(state: GraphState) -> Dict[str, Any]:
        return await structured_planner_node(state, llm_client)

    async def researcher(state: GraphState) -> Dict[str, Any]:
        return await parallel_research_node(state, llm_client)

    async def reporter(state: GraphState) -> Dict[str, Any]:
        return await report_node(state, llm_client)

    async def task_node(state: GraphState) -> Dict[str, Any]:
        return await dispatch_task(state, llm_client)

    async def llm_node(state: GraphState) -> Dict[str, Any]:
        user_message = state.get("user_message", "")
        session_id = state.get("session_id", "default_session")
        history = state.get("history", "")
        web_results = state.get("web_results")
        rag_context = state.get("rag_context")
        sql_result_raw = state.get("sql_result")
        
        tool_called = state.get("tool_called", False)
        tool_success = state.get("tool_success", False)

        history_prefix = f"Conversation History:\n{history}\n\n" if history else ""

        # Enforce anti-hallucination if tool failed
        if tool_called and not tool_success:
            return {"draft_response": "I couldn't find that information in the required database, documents, or search."}

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
                "Answer the user's question concisely using ONLY the retrieved enterprise context below. "
                "If the context contains a relevant excerpt, summarize the explicit facts directly in 1-4 sentences. "
                "Partial answers are allowed: if the document lists only some benefits, policy points, or requirements, answer with exactly those mentioned items. "
                "Do NOT invent, guess, or use general knowledge. "
                "Only return: 'I couldn't find that information in the uploaded company documents.' when the retrieved context is genuinely unrelated or empty.\n\n"
                f"User question: {user_message}\n\n"
                f"Retrieved enterprise context:\n{rag_context}"
            )
        elif sql_result_raw:
            try:
                sql_data = json.loads(sql_result_raw) if isinstance(sql_result_raw, str) else sql_result_raw
                if not sql_data.get("success"):
                    err_msg = sql_data.get("error", "Query execution failed.")
                    return {
                        "draft_response": f"I couldn't execute the requested database query due to a schema or database error: {err_msg}. Please verify available table and column names.",
                        "sql_result": sql_data,
                    }

                if sql_data.get("answer"):
                    prompt = (
                        f"{history_prefix}"
                        "Answer the user's question using ONLY the database-grounded answer below produced from a real "
                        "PostgreSQL query. Do NOT change any numbers, names, or values in that answer — copy them exactly "
                        "into your final response. If the answer contains an error instead of a result, report the error.\n\n"
                        f"User question: {user_message}\n\n"
                        f"Database answer: {sql_data['answer']}"
                    )
                elif sql_data.get("rows") is not None:
                    prompt = (
                        f"{history_prefix}"
                        "Answer the user's question using ONLY the successful database query results below. "
                        "Every number, name, aggregation, and rank must come directly from the JSON results. "
                        "If the result does not contain the number the user asked about, say the database result was "
                        "unavailable rather than inventing a value.\n\n"
                        f"User question: {user_message}\n\n"
                        f"Database query results:\n{json.dumps(sql_data['rows'], indent=2)}"
                    )
                elif "message" in sql_data:
                    # Write transaction fallback message
                    prompt = (
                        f"{history_prefix}"
                        "Answer the user's question using ONLY the successful database transaction results below. "
                        f"User question: {user_message}\n\n"
                        f"Transaction results:\n{json.dumps(sql_data, indent=2)}"
                    )
                else:
                    prompt = (
                        f"{history_prefix}"
                        "The database query executed successfully, but returned 0 rows (empty dataset).\n"
                        "Inform the user concisely that no matching records were found in the database. "
                        "Do NOT invent or guess any numbers.\n\n"
                        f"User question: {user_message}"
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
                "IMPORTANT: If the user asks for sales, revenue, counts, totals, or any business metric that "
                "would come from the enterprise database, do NOT invent or estimate a specific number. "
                "You may only state that this data must be queried from the database when you do not have it. "
                "If the user is asking a follow-up question (e.g., 'just give name only'), refer directly to the conversation history.\n\n"
                f"{history_prefix}"
                f"User: {user_message}"
            )

        response = await llm_client.generate(prompt)

        # Guard against LLM provider/service failure messages leaking to the user
        lowered_response = response.lower().strip()
        if lowered_response.startswith(("groq llm service notice", "groq service notice")) or not response.strip():
            response = "I'm sorry, the AI service is temporarily unavailable. Please try again in a few moments."

        output_state: Dict[str, Any] = {"draft_response": response}

        # Auto-promote substantial Q&A / RAG answer into active session artifact
        if response and len(response) > 20 and "couldn't find" not in response.lower() and tool_called:
            title = f"Q&A: {user_message[:35]}"
            if "kanish" in user_message.lower() or "skills" in user_message.lower():
                title = "Kanishka Kumar Technical Skills"

            sources_list = [state.get("source")] if state.get("source") else []
            artifact_obj = create_artifact(
                artifact_type="text",
                title=title,
                content=response,
                source_documents=sources_list,
                artifact_format="markdown",
            )
            save_session_artifact(session_id, artifact_obj)
            output_state["artifact"] = artifact_obj

        return output_state

    async def web_node(state: GraphState) -> Dict[str, Any]:
        results = search_web(state.get("user_message", ""))
        return {
            "web_results": results,
            "tool_called": True,
            "tool_success": bool(results),
            "source": "Web Search"
        }

    async def reflect(state: GraphState) -> Dict[str, Any]:
        return await reflection_node(state, llm_client)

    async def aggregate(state: GraphState) -> Dict[str, Any]:
        return aggregate_node(state)

    async def final_answer(state: GraphState) -> Dict[str, Any]:
        return final_answer_node(state)

    def route_after_guardrail(state: GraphState) -> str:
        if state.get("guardrail_allowed") is False:
            return "final_answer_node"
        return "supervisor"

    def route_after_approval(state: GraphState) -> str:
        if state.get("requires_approval") is True and state.get("human_approved") is not True:
            return "final_answer_node"
        return "sql_node"

    def route_after_reflection(state: GraphState) -> str:
        res = state.get("reflection_result", {})
        decision = res.get("decision", "PASS")
        retry_count = state.get("retry_count", 0)

        if decision == "RETRY" and retry_count < MAX_REFLECTION_ATTEMPTS:
            return "supervisor"
        return "aggregate_node"

    graph = StateGraph(GraphState)
    graph.add_node("guardrail_node", guardrail)
    graph.add_node("supervisor", supervisor)
    graph.add_node("approval_node", approval)
    graph.add_node("rag_node", rag)
    graph.add_node("sql_node", sql_agent)
    graph.add_node("web_node", web_node)
    graph.add_node("planner_node", planner)
    graph.add_node("researcher_node", researcher)
    graph.add_node("reporter_node", reporter)
    graph.add_node("task_node", task_node)
    graph.add_node("llm_node", llm_node)
    graph.add_node("reflection_node", reflect)
    graph.add_node("aggregate_node", aggregate)
    graph.add_node("final_answer_node", final_answer)

    graph.add_edge(START, "guardrail_node")

    graph.add_conditional_edges(
        "guardrail_node",
        route_after_guardrail,
        {"supervisor": "supervisor", "final_answer_node": "final_answer_node"},
    )

    graph.add_conditional_edges(
        "supervisor",
        lambda state: state.get("route", "direct"),
        {
            "direct": "llm_node",
            "rag": "rag_node",
            "web": "web_node",
            "sql": "approval_node",
            "task": "task_node",
            "planner": "planner_node",
            "research": "planner_node",
        },
    )

    graph.add_conditional_edges(
        "approval_node",
        route_after_approval,
        {"sql_node": "sql_node", "final_response_node": "final_answer_node"},
    )

    graph.add_edge("rag_node", "llm_node")
    graph.add_edge("web_node", "llm_node")
    graph.add_edge("sql_node", "llm_node")
    graph.add_edge("planner_node", "researcher_node")
    graph.add_edge("researcher_node", "reporter_node")
    graph.add_edge("reporter_node", "reflection_node")
    graph.add_edge("task_node", "reflection_node")
    graph.add_edge("llm_node", "reflection_node")

    graph.add_conditional_edges(
        "reflection_node",
        route_after_reflection,
        {"supervisor": "supervisor", "aggregate_node": "aggregate_node"},
    )

    graph.add_edge("aggregate_node", "final_answer_node")
    graph.add_edge("final_answer_node", END)

    return graph.compile()
