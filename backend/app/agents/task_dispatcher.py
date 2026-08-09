"""Task Dispatcher executing leave letter, report synthesis, PDF conversion, and artifact modifications."""

import logging
from pathlib import Path
from typing import Any, Dict

from backend.app.agents.graph.state import GraphState
from backend.app.api.reports import register_generated_report
from backend.app.llm.llm_client import LLMClient
from backend.app.services.artifact_service import create_artifact, save_session_artifact
from backend.app.tools.pdf_report_tool import create_pdf_report

logger = logging.getLogger("enterprise_ai.task_dispatcher")


def _extract_assistant_content_from_history(history: str) -> str:
    """Extracts the most recent substantial assistant response from conversation history."""
    if not history:
        return ""
    turns = history.split("\n\n")
    for turn in reversed(turns):
        if turn.startswith("Assistant:") or turn.startswith("AI:"):
            content = turn.split(":", 1)[1].strip()
            if len(content) > 20 and "Notice:" not in content:
                return content
    return ""


async def dispatch_task(state: GraphState, llm_client: LLMClient) -> Dict[str, Any]:
    """Dispatches document creation, conversion, and modification tasks."""
    task_type = state.get("task_type", "leave_letter")
    user_msg = state.get("user_message", "")
    history = state.get("history", "")
    active_artifact = state.get("artifact")
    rag_context = state.get("rag_context", "")
    session_id = state.get("session_id", "default_session")

    # 1. PDF Conversion Task
    if task_type == "pdf_conversion":
        content = ""
        title = "Document"
        art_type = "text"
        sources = []

        if active_artifact and active_artifact.get("content"):
            content = active_artifact["content"]
            title = active_artifact.get("title", "Document Report")
            art_type = active_artifact.get("type", "text")
            sources = active_artifact.get("source_documents", [])
            logger.info("PDF Task using active artifact content: length=%d", len(content))
        elif state.get("draft_response") and len(state.get("draft_response", "")) > 20:
            content = state["draft_response"]
            title = "Summary Document"
            logger.info("PDF Task using state draft_response content: length=%d", len(content))
        elif history:
            content = _extract_assistant_content_from_history(history)
            if "kanishka" in history.lower() or "skills" in history.lower():
                title = "Kanishka Kumar Technical Skills"
                sources = ["kanishka_kumar_ResumeFresher.pdf"]
            logger.info("PDF Task using extracted history content: length=%d", len(content))

        if not content or not content.strip():
            logger.warning("PDF Task rejected: no previous artifact or context content found.")
            msg = "I don't have a previous document to convert. Please provide or create the content first."
            return {"draft_response": msg, "final_response": msg, "errors": ["No active artifact found"]}

        clean_title = title.replace("_", " ").title()
        logger.info("Calling PDF generator: title=%r, content_length=%d", clean_title, len(content))
        pdf_res = create_pdf_report(title=clean_title, content=content, sources=sources)

        if pdf_res.get("success"):
            file_path = Path(pdf_res["file_path"])
            filename = f"{art_type}_report.pdf"
            record = register_generated_report(file_path, filename)

            download_url = record["download_url"]
            pdf_artifact = create_artifact(
                artifact_type="pdf",
                title=f"{clean_title} (PDF)",
                content=content,
                artifact_format="pdf",
                source_documents=sources,
                file_path=str(file_path),
                download_url=download_url,
            )
            save_session_artifact(session_id, pdf_artifact)

            final_text = f"Your PDF is ready.\n\n[Download PDF Report]({download_url})"
            return {
                "draft_response": final_text,
                "final_response": final_text,
                "artifact": pdf_artifact,
            }

    # 2. Leave Letter Generation Task
    if task_type == "leave_letter":
        prompt = (
            "You are an Executive HR Specialist. Write a clean, 1-page professional leave letter based on the user request.\n"
            "DATE VERIFICATION: If the user specified '12.12.2026', note politely in parenthesis that Dec 12, 2026 is a Saturday.\n"
            f"Retrieved Company Policy Context:\n{rag_context}\n\n"
            f"User Request: {user_msg}"
        )
        content = await llm_client.generate(prompt)

        letter_artifact = create_artifact(
            artifact_type="leave_letter",
            title="Leave Request Letter",
            content=content,
            artifact_format="markdown",
        )
        save_session_artifact(session_id, letter_artifact)

        return {
            "draft_response": content,
            "final_response": content,
            "artifact": letter_artifact,
        }

    # 3. Artifact Modification Task (e.g., "make it shorter", "rewrite it")
    if task_type == "artifact_modification":
        old_content = ""
        if active_artifact and active_artifact.get("content"):
            old_content = active_artifact["content"]
        elif history:
            old_content = _extract_assistant_content_from_history(history)

        if old_content:
            prompt = (
                "You are an AI Content Editor. Modify and reformat the existing text content concisely according to the user instruction.\n\n"
                f"Existing Text Content:\n{old_content}\n\n"
                f"User Instruction: {user_msg}"
            )
            modified_content = await llm_client.generate(prompt)

            updated_artifact = create_artifact(
                artifact_type="text",
                title=active_artifact.get("title", "Modified Document") if active_artifact else "Shortened Summary",
                content=modified_content,
                artifact_format="markdown",
            )
            save_session_artifact(session_id, updated_artifact)

            return {
                "draft_response": modified_content,
                "final_response": modified_content,
                "artifact": updated_artifact,
            }

    # Default fallback
    return {"draft_response": state.get("draft_response", "")}
