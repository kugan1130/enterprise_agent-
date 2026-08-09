"""Dedicated PDF conversion node converting active conversation artifacts to physical PDF files."""

from pathlib import Path
from typing import Any, Dict
from backend.app.agents.graph.state import GraphState
from backend.app.tools.pdf_report_tool import create_pdf_report
from backend.app.api.reports import register_generated_report


def pdf_conversion_node(state: GraphState) -> Dict[str, Any]:
    """Converts current active conversation artifact into a physical PDF file with real download URL."""
    current_artifact = state.get("current_artifact")
    draft_response = state.get("draft_response", "")

    content = ""
    title = "Document"
    artifact_type = "document"

    if current_artifact and current_artifact.get("content"):
        content = current_artifact["content"]
        title = current_artifact.get("title") or "Leave Request Letter"
        artifact_type = current_artifact.get("type", "document")
    elif draft_response and "Notice:" not in draft_response and len(draft_response) > 30:
        content = draft_response
        title = "Conversation Document"

    if not content:
        return {
            "draft_response": "I don't have a previous document in this conversation to convert to PDF.",
            "final_response": "I don't have a previous document in this conversation to convert to PDF.",
        }

    # Generate physical PDF on disk using existing content
    clean_title = title.replace("_", " ").title()
    pdf_result = create_pdf_report(title=clean_title, content=content)

    if pdf_result.get("success"):
        file_path = Path(pdf_result["file_path"])
        readable_filename = f"{artifact_type}_report.pdf"
        record = register_generated_report(file_path, readable_filename)

        download_url = record["download_url"]
        user_label = artifact_type.replace("_", " ").title()

        response_text = (
            f"Your {user_label} PDF is ready.\n\n"
            f"[Download PDF Report]({download_url})"
        )
        return {
            "draft_response": response_text,
            "final_response": response_text,
            "current_artifact": {
                "type": artifact_type,
                "title": title,
                "content": content,
                "pdf_url": download_url,
            },
        }

    return {
        "draft_response": "Failed to create PDF report from the previous document. Please try again.",
        "final_response": "Failed to create PDF report from the previous document. Please try again.",
    }
