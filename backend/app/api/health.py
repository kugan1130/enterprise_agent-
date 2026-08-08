"""Health checks and monitoring endpoints."""

import os
from pathlib import Path
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from backend.app.core.database import SessionLocal
from backend.app.core.redis import get_redis_client

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    """Basic operational health check endpoint."""
    return {"status": "ok"}


@router.get("/health/live")
def liveness_check():
    """Kubernetes / Container liveness probe."""
    return {"status": "live"}


@router.get("/health/ready")
def readiness_check(response: Response):
    """
    Readiness probe verifying PostgreSQL database, Redis cache, and ChromaDB vector store.
    """
    services = {
        "postgres": "unhealthy",
        "redis": "unhealthy",
        "chroma": "unhealthy",
    }
    all_healthy = True

    # 1. Test PostgreSQL database connection
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
            services["postgres"] = "ok"
    except Exception:
        all_healthy = False

    # 2. Test Redis connection
    try:
        r = get_redis_client()
        if r.ping():
            services["redis"] = "ok"
    except Exception:
        all_healthy = False

    # 3. Test ChromaDB path accessibility
    try:
        chroma_dir = Path(__file__).resolve().parents[3] / ".data" / "chroma"
        if chroma_dir.exists() or os.access(chroma_dir.parent, os.W_OK):
            services["chroma"] = "ok"
    except Exception:
        all_healthy = False

    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if all_healthy else "unhealthy",
        "services": services,
    }
