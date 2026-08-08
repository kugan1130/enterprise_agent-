"""Reporter node synthesizing executive content and physical PDF files."""

from typing import Any, Dict
from backend.app.agents.graph.state import GraphState
from backend.app.llm.llm_client import LLMClient
from backend.app.tools.pdf_report_tool import create_pdf_report


async def report_node(state: GraphState, llm_client: LLMClient) -> Dict[str, Any]:
    """Generates structured report text and creates physical PDF file."""
    user_msg = state.get("user_message", "")
    rag_ctx = state.get("rag_context", "")

    prompt = (
        "You are an Executive Business Analyst. "
        "Synthesize a professional, well-structured report for the user request.\n\n"
        f"Retrieved Enterprise Context:\n{rag_ctx}\n\n"
        f"User Request: {user_msg}"
    )

    report_text = await llm_client.generate(prompt)

    # Issue 8 Fix: Generate real PDF file on disk and verify existence
    pdf_result = create_pdf_report(
        title=f"Report: {user_msg[:40]}",
        content=report_text,
    )

    if pdf_result.get("success"):
        filename = pdf_result["filename"]
        final_output = f"# Executive Report\n\n{report_text}\n\n---\n**PDF File Status**: Generated successfully as `{filename}` ({pdf_result['size_bytes']} bytes)."
    else:
        final_output = f"# Executive Report\n\n{report_text}"

    return {"report_output": report_text, "draft_response": final_output}
