"""Report agent node for synthesizing research results into a structured report."""

import json
from typing import Any, Dict

from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient


async def report_node(state: GraphState, llm_client: LLMClient) -> Dict[str, Any]:
    """
    Synthesizes collected research evidence into a structured markdown report.
    Distinguishes between internal enterprise documents, SQL database results, and web search evidence.
    """
    user_message = state.get("user_message", "")
    research_results = state.get("research_results", [])

    formatted_evidence = []
    all_sources = set()

    for idx, item in enumerate(research_results, start=1):
        task_title = item.get("task", f"Task {idx}")
        source_type = item.get("source", "unknown").upper()
        evidence = item.get("evidence", "")
        sources = item.get("sources", [])
        all_sources.update(sources)

        formatted_evidence.append(
            f"### Task {idx}: {task_title} (Source Type: {source_type})\n"
            f"Sources Cited: {', '.join(sources)}\n"
            f"Collected Evidence:\n{evidence}\n"
        )

    evidence_block = "\n\n".join(formatted_evidence) or "No research evidence collected."
    sources_block = "\n".join(f"- {s}" for s in sorted(all_sources)) or "- None"

    prompt = (
        "You are an expert Enterprise Report Agent.\n"
        "Synthesize the collected research evidence below into a comprehensive, professional report.\n\n"
        f"Original Research Request: {user_message}\n\n"
        f"Collected Research Evidence:\n{evidence_block}\n\n"
        "Report Requirements:\n"
        "Create a markdown report containing EXACTLY these sections:\n"
        "1. # Title\n"
        "2. ## Executive Summary\n"
        "3. ## Key Findings\n"
        "4. ## Evidence & Data (Explicitly distinguish between Internal Enterprise Documents, SQL Database Results, and Web Information)\n"
        "5. ## Analysis\n"
        "6. ## Recommendations\n"
        "7. ## Sources Cited\n\n"
        "Strict Guidelines:\n"
        "- Do NOT invent evidence or make up unsupported facts.\n"
        "- If information for a section is missing or unavailable, explicitly state that it was not found in the evidence.\n"
        "- Ensure the Sources section lists all verified source documents, databases, and search channels used."
    )

    report_md = await llm_client.generate(prompt)

    return {
        "report_output": report_md,
        "draft_response": report_md,
    }
