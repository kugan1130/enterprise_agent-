"""Planner node for multi-agent workflows."""

import json
from typing import Any, Dict
from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient

async def planner_node(state: GraphState, llm_client: LLMClient) -> Dict[str, Any]:
    """Generates a structured research plan specifying which agents to run concurrently."""
    current_query = state.get("current_query") or state.get("user_message", "")
    prompt = (
        "You are the Planner Agent. The user's query requires multiple tools to answer fully.\n"
        "Analyze the query and decide which agents must be run.\n"
        "Options:\n"
        "- 'RAG' (for uploaded documents, policies, resumes)\n"
        "- 'SQL' (for exact database metrics, sales, revenue)\n"
        "- 'WEB' (for online internet searches and latest news)\n\n"
        "Example Query: 'Tell me remote policy, Q4 revenue, and search online latest AI news.'\n"
        "Example Output: {\"tasks\": [\"RAG\", \"SQL\", \"WEB\"]}\n\n"
        f"Query to plan: {current_query}\n\n"
        "Return ONLY a JSON object: {\"tasks\": [\"<AGENT1>\", \"<AGENT2>\", ...]}"
    )
    try:
        response = await llm_client.generate(prompt)
        cleaned_json = response.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned_json)
        tasks = data.get("tasks", ["RAG", "SQL", "WEB"])  # fallback to all if parsing fails
    except Exception:
        tasks = ["RAG", "SQL", "WEB"]

    return {"research_plan": tasks}
