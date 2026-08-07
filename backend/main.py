import sys
from pathlib import Path
from typing import Any, cast

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.core.config import settings
from app.llm.groq_provider import GroqProvider
from app.llm.llm_client import LLMClient
from services.chat_service import ChatService


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)
    provider = GroqProvider()
    llm_client = LLMClient(provider)
    app.state.chat_service = ChatService(llm_client)
    app.include_router(chat_router)
    return app


app = create_app()

