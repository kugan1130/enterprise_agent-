"""Redis connection management reading credentials directly from settings.REDIS_URL."""

import logging
from typing import Any, Optional
from backend.app.core.config import settings

logger = logging.getLogger("enterprise_ai.redis")
_redis_client: Optional[Any] = None


class RedisService:
    def __init__(self):
        self._client: Optional[Any] = None

    def get_client(self) -> Optional[Any]:
        if self._client is not None:
            try:
                if self._client.ping():
                    return self._client
            except Exception:
                self._client = None

        if not settings.REDIS_URL:
            return None

        try:
            import redis
            client = redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                protocol=2,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
            )
            if client.ping():
                self._client = client
                logger.info("Connected to Redis server successfully at %s", settings.REDIS_URL)
                return self._client
        except Exception as err:
            logger.info("Redis server not reachable at %s (%s). Using in-memory fallback.", settings.REDIS_URL, err)

        self._client = None
        return None

    def check_health(self) -> str:
        """Returns the health status of the Redis connection."""
        try:
            client = self.get_client()
            if client is not None and client.ping():
                return "healthy"
        except Exception:
            pass
        return "healthy (in-memory fallback)"

_redis_service = RedisService()

def get_redis_client() -> Optional[Any]:
    """Returns a connected Redis client using settings.REDIS_URL credentials if available."""
    return _redis_service.get_client()

def get_redis_service() -> RedisService:
    """Returns the centralized Redis service."""
    return _redis_service
