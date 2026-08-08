import sys
from pathlib import Path

# Allow this module to run directly with `python backend/main.py`.
project_dir = Path(__file__).resolve().parent.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from fastapi import FastAPI

from backend.app.api.auth import router as auth_router
from backend.app.api.chat import router as chat_router
from backend.app.api.documents import router as documents_router
from backend.app.core.config import settings
from backend.app.core.database import engine
from backend.app.core.middleware import CorrelationIdMiddleware, enterprise_exception_handler
from backend.app.llm.groq_provider import GroqProvider
from backend.app.llm.llm_client import LLMClient
from backend.app.models.user import Base
from backend.services.chat_service import ChatService


def create_app() -> FastAPI:
    # Create DB tables if they don't exist
    Base.metadata.create_all(bind=engine)

    app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

    # Middleware & Error handling
    app.add_middleware(CorrelationIdMiddleware)
    app.add_exception_handler(Exception, enterprise_exception_handler)

    provider = GroqProvider()
    llm_client = LLMClient(provider)
    app.state.chat_service = ChatService(llm_client)

    app.include_router(chat_router)
    app.include_router(auth_router)
    app.include_router(documents_router)
    return app


app = create_app()
