"""Enterprise HTTP Correlation ID and exception handler middleware."""

import uuid
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Injects or propagates X-Correlation-ID headers across HTTP request cycles."""

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or uuid.uuid4().hex
        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


async def enterprise_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler returning clean JSON error responses."""
    correlation_id = getattr(request.state, "correlation_id", "N/A")
    print(f"Unhandled Exception [{correlation_id}]: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc) if str(exc) else "An unexpected internal server error occurred.",
                "correlation_id": correlation_id,
            }
        },
    )
