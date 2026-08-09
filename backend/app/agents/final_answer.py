"""Final Answer Node constructing normalized user-facing response data."""

from typing import Any, Dict
from backend.app.agents.graph.state import GraphState


def final_answer_node(state: GraphState) -> Dict[str, Any]:
    """Constructs final structured response dictionary for frontend consumption."""
    draft = state.get("draft_response", "")
    route = state.get("route", "direct")
    sources = state.get("sources", [])
    chart_data = state.get("chart_data")
    artifact = state.get("artifact")
    guardrail_allowed = state.get("guardrail_allowed")

    if guardrail_allowed is False:
        answer_text = f"Security Guardrail Notice: {state.get('guardrail_reason', 'Request blocked.')}"
    elif draft:
        answer_text = draft
    else:
        answer_text = state.get("final_response", "Request completed.")

    structured_answer = {
        "answer": answer_text,
        "route": route,
        "sources": sources,
        "chart_data": chart_data,
        "artifact": {
            "artifact_id": artifact.get("artifact_id") if artifact else None,
            "type": artifact.get("type") if artifact else None,
            "title": artifact.get("title") if artifact else None,
            "download_url": artifact.get("download_url") if artifact else None,
        } if artifact else None,
    }

    return {
        "final_answer": structured_answer,
        "final_response": answer_text,
    }
