import logging
from typing import Any, Dict, List
from langgraph.graph import END, START, StateGraph
from langchain_core.messages import HumanMessage

from backend.app.agents.graph.state import AgentState
from backend.app.agents.supervisor import supervisor_node
from backend.app.agents.rag import rag_node
from backend.app.agents.web import web_node
from backend.app.agents.sql import sql_node
from backend.app.agents.llm import context_builder_and_llm_node
from backend.app.core.memory import add_conversation_turn, get_conversation_messages

from backend.app.agents.guardrail import input_guardrail_node

logger = logging.getLogger("enterprise_ai.workflow")


async def load_context_node(state: AgentState) -> Dict[str, Any]:
    """Loads recent session history as native LangChain BaseMessage primitives."""
    session_id = state.get("session_id", "default_session")
    user_query = state.get("current_query", "")

    history_messages = get_conversation_messages(session_id, max_turns=10)
    messages = list(history_messages)
    if user_query and (not messages or messages[-1].content != user_query):
        messages.append(HumanMessage(content=user_query))

    return {
        "messages": messages,
        "session_id": session_id,
        "current_query": user_query,
    }


async def save_memory_node(state: AgentState) -> Dict[str, Any]:
    """Persists completed user query and final AI answer turn to session memory store."""
    session_id = state.get("session_id", "default_session")
    query = state.get("current_query", "")
    response = state.get("final_response", "")

    if query and response:
        add_conversation_turn(session_id, query, response)
        logger.info("Saved conversation turn for session %s", session_id)

    return {}


def route_after_guardrail(state: AgentState) -> str:
    """Routes to supervisor if input is allowed, or save_memory if blocked by guardrail."""
    if state.get("guardrail_allowed") is False:
        return "save_memory"
    return "supervisor"


def route_after_supervisor(state: AgentState) -> List[str]:
    """Determines target node(s) based on supervisor route selection."""
    routes = state.get("routes", ["conversation"])
    targets = []
    if "web" in routes:
        targets.append("web_node")
    if "rag" in routes:
        targets.append("rag_node")
    if "sql" in routes:
        targets.append("sql_node")

    if not targets:
        targets.append("context_builder")

    return targets


def create_workflow():
    """Builds and compiles the production minimal LangGraph agent orchestration graph."""
    graph = StateGraph(AgentState)

    graph.add_node("load_context", load_context_node)
    graph.add_node("guardrail", input_guardrail_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("rag_node", rag_node)
    graph.add_node("web_node", web_node)
    graph.add_node("sql_node", sql_node)
    graph.add_node("context_builder", context_builder_and_llm_node)
    graph.add_node("save_memory", save_memory_node)

    # Edge connections
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "guardrail")

    graph.add_conditional_edges(
        "guardrail",
        route_after_guardrail,
        {
            "supervisor": "supervisor",
            "save_memory": "save_memory",
        },
    )

    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "web_node": "web_node",
            "rag_node": "rag_node",
            "sql_node": "sql_node",
            "context_builder": "context_builder",
        },
    )

    graph.add_edge("rag_node", "context_builder")
    graph.add_edge("web_node", "context_builder")
    graph.add_edge("sql_node", "context_builder")

    graph.add_edge("context_builder", "save_memory")
    graph.add_edge("save_memory", END)

    return graph.compile()
