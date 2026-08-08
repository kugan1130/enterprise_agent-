"""Redis connection management with optional dynamic fallback."""

from typing import Any, Optional
from backend.app.core.config import settings

_redis_client: Optional[Any] = None


def get_redis_client() -> Optional[Any]:
    """Returns a connected Redis client if available, else None for in-memory fallback."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        import redis
        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=2)
        if client.ping():
            _redis_client = client
            return _redis_client
    except Exception as err:
        print(f"Redis connection notice ({err}). Proceeding with in-memory fallback...")

    return None
