"""Parallel Research agent node executing planned tasks concurrently."""

import asyncio
import json
from typing import Any, Dict, List

from backend.app.agents.graph.state import GraphState
from backend.app.core.permissions import check_tool_permission
from backend.app.llm.llm_client import LLMClient
from backend.app.rag.retriever import retrieve
from backend.app.tools.sql_tool import execute_sql_query
from backend.app.tools.web_search import search_web


async def _execute_single_task(task_item: Dict[str, str], llm_client: LLMClient) -> Dict[str, Any]:
    """
    Executes a single research task based on its source (sql, rag, web)
    and collects evidence and source metadata.
    """
    task_id = task_item.get("task_id", "task")
    task_desc = task_item.get("task", "")
    source = task_item.get("source", "web").lower()

    if source == "sql":
        sql_prompt = (
            "Generate a single read-only SQL SELECT query for this research task.\n"
            "Database schema: Table 'sales' with columns (id, customer_name, region, product, amount, sale_date).\n"
            "Return ONLY raw SQL.\n\n"
            f"Task: {task_desc}"
        )
        raw_sql = await llm_client.generate(sql_prompt)
        clean_sql = raw_sql.replace("```sql", "").replace("```", "").strip()
        op = clean_sql.split()[0].lower() if clean_sql else "select"
        perm = check_tool_permission("sql", op)
        if not perm["permitted"]:
            return {
                "task_id": task_id,
                "task": task_desc,
                "source": "sql",
                "evidence": f"Permission Error: {perm['reason']}",
                "sources": ["PostgreSQL DB"],
            }
        sql_res = execute_sql_query(clean_sql)
        return {
            "task_id": task_id,
            "task": task_desc,
            "source": "sql",
            "evidence": json.dumps(sql_res),
            "sources": ["PostgreSQL DB: sales table"],
        }

    elif source == "rag":
        rag_results = retrieve(task_desc, limit=3)
        sources = list({doc["metadata"]["source"] for doc in rag_results if "metadata" in doc and "source" in doc["metadata"]})
        evidence_text = "\n\n".join(
            f"Source: {doc['metadata'].get('source', 'Doc')}\n{doc['text']}" for doc in rag_results
        ) or "No relevant enterprise documents found."
        return {
            "task_id": task_id,
            "task": task_desc,
            "source": "rag",
            "evidence": evidence_text,
            "sources": sources or ["Enterprise Documents"],
        }

    else: # web
        web_res = search_web(task_desc)
        return {
            "task_id": task_id,
            "task": task_desc,
            "source": "web",
            "evidence": web_res,
            "sources": ["Tavily Web Search"],
        }


async def parallel_research_node(state: GraphState, llm_client: LLMClient) -> Dict[str, Any]:
    """
    Executes all sub-tasks in research_plan concurrently using asyncio.gather.
    """
    tasks = state.get("research_plan", [])
    if not tasks:
        return {"research_results": []}

    # Execute all planned sub-tasks in parallel
    results = await asyncio.gather(*[_execute_single_task(t, llm_client) for t in tasks])

    return {"research_results": list(results)}
