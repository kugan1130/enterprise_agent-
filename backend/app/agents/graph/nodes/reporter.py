"""Reporter node synthesizing executive content and generating secure download links."""

from typing import Any, Dict
from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient
from backend.app.tools.pdf_report_tool import create_pdf_report
from backend.app.api.reports import register_generated_report
from pathlib import Path


async def report_node(state: GraphState, llm_client: LLMClient) -> Dict[str, Any]:
    """Synthesizes report text from retrieved context and creates a real PDF file on disk."""
    user_msg = state.get("current_query") or state.get("user_message", "")
    rag_ctx = state.get("rag_context", "")
    agent_results = state.get("agent_results", [])
    
    # Combine context from RAG if single route, or all successful agents if planner route
    combined_context = rag_ctx
    if agent_results:
        successful_results = [res["result"] for res in agent_results if res.get("tool_success")]
        combined_context = "\n\n".join(successful_results)

    # Ground report content strictly in retrieved enterprise context
    if combined_context and "couldn't find" not in combined_context.lower():
        prompt = (
            "You are an Executive Business Analyst. "
            "Synthesize a professional, 500-word report for the user request. "
            "Use clear subheadings and bullet points.\n"
            "STRICT GROUNDING: Use ONLY information supported by the retrieved context below. "
            "Do NOT invent unmentioned policies or topics.\n\n"
            f"Retrieved Context:\n{combined_context}\n\n"
            f"User Request: {user_msg}"
        )
    else:
        prompt = (
            "You are an Executive Business Analyst. "
            "Write a concise executive summary stating that the report could not be generated due to lack of retrieved information. "
            "Do NOT fabricate company policies or unmentioned rules.\n\n"
            f"User Request: {user_msg}"
        )

    report_text = await llm_client.generate(prompt)

    # Generate physical PDF on disk
    pdf_result = create_pdf_report(
        title=f"Report: {user_msg[:40]}",
        content=report_text,
    )

    if pdf_result.get("success"):
        file_path = Path(pdf_result["file_path"])
        record = register_generated_report(file_path, pdf_result["filename"])

        download_url = record["download_url"]
        filename = record["filename"]

        final_output = (
            f"# Executive Policy Report\n\n"
            f"{report_text}\n\n"
            f"---\n"
            f"### Download Report PDF\n"
            f"Your PDF report has been generated: **[{filename}]({download_url})**\n\n"
            f"[Download PDF Report]({download_url})"
        )
    else:
        final_output = f"# Executive Policy Report\n\n{report_text}"

    return {"report_output": report_text, "draft_response": final_output}
