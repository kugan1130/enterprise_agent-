"""ChatService business logic and workflow orchestration with session artifact memory."""

import json
import time
import uuid
from typing import Any, AsyncGenerator, Dict, Optional

from backend.app.agents.graph.workflow import create_workflow
from backend.app.services.artifact_service import get_active_artifact, save_session_artifact


class ChatService:
    """
    Handles chat business logic, session orchestration, SSE event streaming, and artifact persistence.
    """

    def __init__(self, llm_client: Optional[Any] = None) -> None:
        self._workflow = create_workflow()

    async def ask(self, prompt: str, session_id: str = "default_session", user_id: Optional[int] = None) -> str:
        """
        Send a user prompt through the minimal LangGraph workflow and return final answer.
        """
        result = await self._workflow.ainvoke(
            {
                "current_query": prompt,
                "session_id": session_id,
                "user_id": user_id,
            }
        )

        artifact = result.get("artifact")
        if artifact:
            save_session_artifact(session_id, artifact)

        response = result.get("final_response", "")
        return response

    async def ask_stream(
        self, prompt: str, session_id: str = "default_session", user_id: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """
        Processes a prompt and streams structured progress events and response tokens via SSE format.
        Includes request_id for concurrent stream tracking.
        """
        request_id = f"req_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"

        # 1. Activity Event: Supervisor evaluation
        yield f"data: {json.dumps({'request_id': request_id, 'type': 'activity', 'event': 'status', 'message': 'Evaluating request routing supervisor...'})}\n\n"

        result = await self._workflow.ainvoke(
            {
                "current_query": prompt,
                "session_id": session_id,
                "user_id": user_id,
            }
        )

        artifact = result.get("artifact")
        if artifact:
            save_session_artifact(session_id, artifact)
            yield f"data: {json.dumps({'request_id': request_id, 'type': 'artifact', 'event': 'artifact', 'artifact': artifact})}\n\n"

        routes = result.get("routes", ["conversation"])
        primary_route = routes[0] if routes else "conversation"
        yield f"data: {json.dumps({'request_id': request_id, 'type': 'route', 'event': 'route_selected', 'route': primary_route, 'routes': routes})}\n\n"

        yield f"data: {json.dumps({'request_id': request_id, 'type': 'activity', 'event': 'status', 'message': f'Executed pipeline: {str(routes).upper()}'})}\n\n"

        response = result.get("final_response", "")

        # Stream response tokens in small chunks for smooth UI output
        chunk_size = 12
        for i in range(0, len(response), chunk_size):
            chunk = response[i : i + chunk_size]
            yield f"data: {json.dumps({'request_id': request_id, 'type': 'token', 'event': 'token', 'chunk': chunk, 'content': chunk})}\n\n"

        yield f"data: {json.dumps({'request_id': request_id, 'type': 'activity', 'event': 'status', 'message': 'Execution completed.'})}\n\n"

        # Final Event
        yield f"data: {json.dumps({'request_id': request_id, 'type': 'final', 'event': 'completed', 'content': response, 'response': response, 'route': primary_route})}\n\n"
