from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.app.api.auth import get_current_user
from backend.app.models.user import User
from backend.services.chat_service import ChatService


router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message to send to the chat service.")
    session_id: str = Field(default="default_session", description="Session identifier for memory isolation.")


class ChatResponse(BaseModel):
    response: str


def get_chat_service(request: Request) -> ChatService:
    """Retrieve the application-configured chat service."""
    chat_service = getattr(request.app.state, "chat_service", None)
    if chat_service is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat service is not configured.",
        )
    return chat_service


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    """Non-streaming chat response endpoint."""
    response = await chat_service.ask(payload.message, payload.session_id)
    return ChatResponse(response=response)


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
):
    """Event-driven Server-Sent Events (SSE) streaming chat endpoint."""
    return StreamingResponse(
        chat_service.ask_stream(payload.message, payload.session_id),
        media_type="text/event-stream",
    )
