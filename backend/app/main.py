"""Main FastAPI application entry point for Enterprise AI Assistant."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.database import Base, engine
from backend.app.api.health import router as health_router
from backend.app.api.auth import router as auth_router
from backend.app.api.chat import router as chat_router
from backend.app.api.reports import router as reports_router
from backend.app.api.documents import router as documents_router
from backend.services.chat_service import ChatService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enterprise_ai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown procedures."""
    logger.info("Initializing Enterprise AI Assistant backend database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created successfully.")
    except Exception as err:
        logger.error("Failed to initialize database tables: %s", err)

    try:
        from backend.app.core.seed import seed_all
        seed_all()
    except Exception as err:
        logger.error("Startup seeding failed: %s", err)

    logger.info("Initializing ChatService workflow...")
    app.state.chat_service = ChatService()
    logger.info("ChatService initialized.")

    yield

    logger.info("Shutting down Enterprise AI Assistant backend.")


app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise Multi-Agent AI Assistant API backend with RAG, SQL, Web Search, and Auth.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.ALLOWED_ORIGINS] if settings.ALLOWED_ORIGINS != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(reports_router)

# Note: documents_router will be included after building backend/app/api/documents.py
