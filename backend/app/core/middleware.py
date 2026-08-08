"""Middleware for Correlation ID tracking, structured logging, and unified error handling."""

import logging
import uuid
from typing import Any, Dict
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - [%(levelname)s] - correlation_id=%(correlation_id)s - %(message)s",
)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that injects an X-Request-ID header into every incoming request and response."""

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = correlation_id
        return response


def get_request_id(request: Request) -> str:
    """Retrieve correlation ID from request state."""
    return getattr(request.state, "correlation_id", "no-id")


async def enterprise_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Standardized JSON error handler returning safe, structured error objects.
    Prevents leakage of raw stack traces, API keys, or database credentials.
    """
    correlation_id = get_request_id(request)

    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        error_code = "HTTP_ERROR"
        if status_code == 401:
            error_code = "UNAUTHORIZED"
        elif status_code == 403:
            error_code = "FORBIDDEN"
        elif status_code == 404:
            error_code = "NOT_FOUND"
        elif status_code == 400:
            error_code = "BAD_REQUEST"

        message = str(exc.detail)
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_code = "INTERNAL_SERVER_ERROR"
        message = "An internal server error occurred. Please contact system administration."

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code,
                "message": message,
                "correlation_id": correlation_id,
            }
        },
    )
