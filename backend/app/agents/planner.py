"""Planner Node generating structured multi-step execution plans for complex requests."""

import json
from typing import Any, Dict, List
from pydantic import BaseModel, Field

from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient


class PlanStep(BaseModel):
    step: int
    agent: str = Field(description="Agent capability: sql, web, rag, aggregation, or report")
    purpose: str


class StructuredPlan(BaseModel):
    steps: List[PlanStep]


async def planner_node(state: GraphState, llm_client: LLMClient) -> Dict[str, Any]:
    """Generates structured step plan for complex analytical queries."""
    user_msg = state.get("user_message", "")

    prompt = (
        "You are an Executive Task Planner. "
        "Decompose the complex user query into a structured multi-step plan.\n"
        "Available Agents: 'sql' (database queries), 'web' (live search), 'rag' (policy/documents), 'aggregation' (synthesis).\n\n"
        f"User Query: {user_msg}\n\n"
        "Return ONLY JSON in this shape: {\"steps\": [{\"step\": 1, \"agent\": \"sql\", \"purpose\": \"...\"}]}"
    )

    try:
        response_text = await llm_client.generate(prompt)
        cleaned_json = response_text.replace("```json", "").replace("```", "").strip()
        plan_obj = StructuredPlan.model_validate_json(cleaned_json)
        return {
            "research_plan": [s.model_dump() for s in plan_obj.steps],
            "current_query": user_msg,
        }
    except Exception as err:
        print(f"Planner fallback notice ({err})...")
        fallback_steps = [
            {"step": 1, "agent": "sql", "purpose": "Retrieve SQL database metrics"},
            {"step": 2, "agent": "web", "purpose": "Search live industry trends"},
            {"step": 3, "agent": "aggregation", "purpose": "Synthesize combined report"},
        ]
        return {"research_plan": fallback_steps, "current_query": user_msg}
