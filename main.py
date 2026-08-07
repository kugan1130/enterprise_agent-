from fastapi import FastAPI

from backend.app.api.chat import router as chat_router
from backend.app.core.config import settings
from backend.app.llm.llm_client import LLMClient
from backend.app.llm.groq_provider import GroqProvider
from backend.services.chat_service import ChatService


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
    )

    # Create the concrete LLM provider.
    provider = GroqProvider()

    # Wrap the provider with the provider-agnostic client.
    llm_client = LLMClient(provider)

    # Inject the LLM client into the application service.
    app.state.chat_service = ChatService(llm_client)

    # Register API routes.
    app.include_router(chat_router)

    return app


app = create_app()
