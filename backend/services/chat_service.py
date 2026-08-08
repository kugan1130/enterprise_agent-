"""ChatService business logic and workflow orchestration."""

import json
from typing import AsyncGenerator

from backend.app.agents.graph.workflow import create_workflow
from backend.app.core.memory import (
    add_conversation_turn,
    format_history_as_text,
    get_conversation_history,
)
from backend.app.llm.llm_client import LLMClient


class ChatService:
    """
    Handles chat business logic, memory persistence, and agent workflow execution.
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

        result = await self._workflow.ainvoke(
            {
                "user_message": prompt,
                "session_id": session_id,
                "history": history_text,
            }
        )
        response = result.get("final_response", "")
        add_conversation_turn(session_id, prompt, response)
        return response

    async def ask_stream(
        self, prompt: str, session_id: str = "default_session"
    ) -> AsyncGenerator[str, None]:
        """
        Processes a prompt and streams progress events and response tokens via SSE format.
        """
        history = get_conversation_history(session_id)
        history_text = format_history_as_text(history)

        yield f"data: {json.dumps({'event': 'status', 'message': 'Evaluating request guardrails & routing...'})}\n\n"

        result = await self._workflow.ainvoke(
            {
                "user_message": prompt,
                "session_id": session_id,
                "history": history_text,
            }
        )

        route = result.get("route", "direct")
        yield f"data: {json.dumps({'event': 'route_selected', 'route': route})}\n\n"

        response = result.get("final_response", "")

        # Stream response tokens in small chunks
        chunk_size = 15
        for i in range(0, len(response), chunk_size):
            chunk = response[i : i + chunk_size]
            yield f"data: {json.dumps({'event': 'token', 'chunk': chunk})}\n\n"

        yield f"data: {json.dumps({'event': 'completed', 'response': response})}\n\n"

        # Record conversation turn in short-term memory
        add_conversation_turn(session_id, prompt, response)
