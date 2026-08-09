"""ChatService business logic and workflow orchestration with session artifact memory."""

import json
import time
import uuid
from typing import Any, AsyncGenerator, Dict

from backend.app.agents.graph.workflow import create_workflow
from backend.app.core.memory import (
    add_conversation_turn,
    format_history_as_text,
    get_conversation_history,
)
from backend.app.llm.llm_client import LLMClient
from backend.app.services.artifact_service import (
    get_active_artifact,
    save_session_artifact,
)


class ChatService:
    """
    Handles chat business logic, memory persistence, artifact tracking, and agent workflow execution.
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm
        self._workflow = create_workflow(llm)

    async def ask(self, prompt: str, session_id: str = "default_session") -> str:
        """
        Send a user prompt through the multi-agent workflow and return final answer.
        """
        history = get_conversation_history(session_id)
        history_text = format_history_as_text(history)
        active_art = get_active_artifact(session_id)

        result = await self._workflow.ainvoke(
            {
                "user_message": prompt,
                "session_id": session_id,
                "history": history_text,
                "artifact": active_art,
            }
        )

        if "artifact" in result and result["artifact"]:
            save_session_artifact(session_id, result["artifact"])

        response = result.get("final_response", "")
        add_conversation_turn(session_id, prompt, response)
        return response

    async def ask_stream(
        self, prompt: str, session_id: str = "default_session"
    ) -> AsyncGenerator[str, None]:
        """
        Processes a prompt and streams structured progress events and response tokens via SSE format.
        Includes request_id for concurrent stream tracking.
        """
        request_id = f"req_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
        history = get_conversation_history(session_id)
        history_text = format_history_as_text(history)
        active_art = get_active_artifact(session_id)

        # 1. Activity Event: Guardrail evaluation
        yield f"data: {json.dumps({'request_id': request_id, 'type': 'activity', 'event': 'status', 'message': 'Evaluating request guardrails...'})}\n\n"

        # 2. Activity Event: Context & Routing evaluation
        yield f"data: {json.dumps({'request_id': request_id, 'type': 'activity', 'event': 'status', 'message': 'Evaluating context & routing supervisor...'})}\n\n"

        result = await self._workflow.ainvoke(
            {
                "user_message": prompt,
                "session_id": session_id,
                "history": history_text,
                "artifact": active_art,
            }
        )

        artifact = result.get("artifact")
        if artifact:
            save_session_artifact(session_id, artifact)
            yield f"data: {json.dumps({'request_id': request_id, 'type': 'artifact', 'event': 'artifact', 'artifact': artifact})}\n\n"

        route = result.get("route", "direct")
        yield f"data: {json.dumps({'request_id': request_id, 'type': 'route', 'event': 'route_selected', 'route': route})}\n\n"

        yield f"data: {json.dumps({'request_id': request_id, 'type': 'activity', 'event': 'status', 'message': f'Executed agent pipeline: {route.upper()}'})}\n\n"

        response = result.get("final_response", "")

        # Stream response tokens in small chunks
        chunk_size = 12
        for i in range(0, len(response), chunk_size):
            chunk = response[i : i + chunk_size]
            yield f"data: {json.dumps({'request_id': request_id, 'type': 'token', 'event': 'token', 'chunk': chunk, 'content': chunk})}\n\n"

        yield f"data: {json.dumps({'request_id': request_id, 'type': 'activity', 'event': 'status', 'message': 'Execution completed.'})}\n\n"

        # Final Event
        yield f"data: {json.dumps({'request_id': request_id, 'type': 'final', 'event': 'completed', 'content': response, 'response': response, 'route': route})}\n\n"

        # Record conversation turn in short-term memory (EXCLUDING internal events)
        add_conversation_turn(session_id, prompt, response)
