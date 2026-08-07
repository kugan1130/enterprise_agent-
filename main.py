import sys
from pathlib import Path

# Ensure backend directory is in sys.path so modules like `app` and `services` can be imported
backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.core.config import settings
from app.llm.groq_provider import GroqProvider
from app.llm.llm_client import LLMClient
from services.chat_service import ChatService


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
    )

    # Create the concrete LLM provider and wrap in LLMClient.
    provider = GroqProvider()
    llm_client = LLMClient(provider)

    # Inject the service into the application state.
    app.state.chat_service = ChatService(llm_client)

    # Register API routes.
    app.include_router(chat_router)

    return app


app = create_app()

