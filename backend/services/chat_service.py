from backend.app.agents.graph.workflow import create_workflow
from backend.app.core.memory import (
    add_conversation_turn,
    format_history_as_text,
    get_conversation_history,
)
from backend.app.llm.llm_client import LLMClient


class ChatService:
    """
    Handles chat-related business logic and manages session-isolated Redis conversation memory.
    """

    def __init__(self, llm: LLMClient) -> None:
        """
        Store the LLM implementation and workflow.

        Args:
            llm: Any LLMClient instance.
        """
        self._llm = llm
        self._workflow = create_workflow(llm)

    async def ask(self, prompt: str, session_id: str = "default_session") -> str:
        """
        Processes a user prompt within a session, loading and saving memory in Redis.

        Args:
            prompt: User input text.
            session_id: Unique session identifier for memory isolation.

        Returns:
            Model response.
        """
        # 1. Retrieve prior conversation history for this session from Redis
        history = get_conversation_history(session_id)
        history_text = format_history_as_text(history)

        # 2. Invoke LangGraph workflow with message and prior history context
        result = await self._workflow.ainvoke(
            {
                "user_message": prompt,
                "session_id": session_id,
                "history": history_text,
            }
        )

        response = result.get("final_response", "")

        # 3. Store the turn (user & assistant messages) into Redis key conversation:{session_id}
        add_conversation_turn(session_id, prompt, response)

        return response

    async def ask_stream(self, prompt: str, session_id: str = "default_session"):
        """
        Processes a prompt and streams progress events and response tokens via SSE format.
        """
        import json

        # 1. Retrieve prior conversation history
        history = get_conversation_history(session_id)
        history_text = format_history_as_text(history)

        yield f"data: {json.dumps({'event': 'status', 'message': 'Evaluating request guardrails...'})}\n\n"

        # 2. Invoke workflow
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

        # 3. Store turn in Redis
        add_conversation_turn(session_id, prompt, response)
