import logging
from typing import Any, Dict
from backend.app.agents.graph.state import AgentState
from backend.app.tools.web_search import search_web

logger = logging.getLogger("enterprise_ai.web_agent")


async def web_node(state: AgentState) -> Dict[str, Any]:
    """Executes live web search tool via Tavily API."""
    query = str(state.get("current_query") or (state["messages"][-1].content if state.get("messages") else ""))
    try:
        res = search_web.invoke({"query": query})
        return {"web_results": [res]}
    except Exception as err:
        logger.error("Web Agent error: %s", err)
        return {"web_results": [], "error": f"Web Error: {err}"}
