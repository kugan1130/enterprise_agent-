"""Health check and readiness monitoring endpoints."""

import os
from pathlib import Path
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from backend.app.core.database import SessionLocal
from backend.app.core.redis import get_redis_service
from backend.app.core.chroma import get_chroma_service

router = APIRouter(tags=["health"])

@router.get("/health")
def health_check():
    """Operational health check endpoint for all backend services."""
    services = {
        "postgres": "unhealthy",
        "redis": "unhealthy",
        "chroma": "unhealthy",
    }
    all_healthy = True

    # 1. Test Database connection
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
            services["postgres"] = "healthy"
    except Exception:
        all_healthy = False

    # 2. Test Redis / Memory Store connection
    redis_status = get_redis_service().check_health()
    if redis_status.startswith("healthy"):
        services["redis"] = "healthy"
    else:
        services["redis"] = "unhealthy"
        all_healthy = False

    # 3. Test ChromaDB path accessibility
    chroma_status = get_chroma_service().health_check()
    if chroma_status == "healthy":
        services["chroma"] = "healthy"
    else:
        services["chroma"] = "unhealthy"
        all_healthy = False

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "postgres": services["postgres"],
        "redis": services["redis"],
        "chroma": services["chroma"],
    }
