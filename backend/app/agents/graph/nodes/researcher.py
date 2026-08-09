"""Parallel multi-agent execution node."""

import asyncio
from typing import Any, Dict
from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient
from backend.app.agents.graph.nodes.rag import rag_node
from backend.app.agents.graph.nodes.sql import sql_node
from backend.app.tools.web_search import search_web

async def parallel_research_node(state: GraphState, llm_client: LLMClient) -> Dict[str, Any]:
    """Executes parallel information gathering based on the research plan."""
    plan = state.get("research_plan", [])
    
    tasks = []
    task_names = []
    
    if "RAG" in plan:
        tasks.append(rag_node(state))
        task_names.append("RAG")
    if "SQL" in plan:
        tasks.append(sql_node(state, llm_client))
        task_names.append("SQL")
    if "WEB" in plan:
        async def web_wrapper():
            results = search_web(state.get("current_query") or state.get("user_message", ""))
            return {
                "web_results": results,
                "tool_called": True,
                "tool_success": bool(results),
                "source": "Web Search"
            }
        tasks.append(web_wrapper())
        task_names.append("WEB")

    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    agent_results = []
    for i, res in enumerate(results):
        name = task_names[i]
        if isinstance(res, Exception):
            agent_results.append({
                "route": name,
                "tool_called": True,
                "tool_success": False,
                "source": name,
                "error": str(res),
                "result": f"{name} execution failed due to an exception."
            })
        elif isinstance(res, dict):
            # Extract standard fields
            tool_success = res.get("tool_success", False)
            source = res.get("source", name)
            
            # Map specific results back to a unified 'result' string for the final LLM
            if name == "RAG":
                result_text = res.get("rag_context", "")
            elif name == "SQL":
                sql_raw = res.get("sql_result")
                if isinstance(sql_raw, dict) and sql_raw.get("answer"):
                    result_text = sql_raw["answer"]
                else:
                    import json
                    result_text = json.dumps(sql_raw) if sql_raw else "Database error"
            elif name == "WEB":
                result_text = str(res.get("web_results", ""))
            else:
                result_text = str(res)
            
            agent_results.append({
                "route": name,
                "tool_called": res.get("tool_called", True),
                "tool_success": tool_success,
                "source": source,
                "result": result_text,
                "error": res.get("error")
            })

    return {"agent_results": agent_results}
