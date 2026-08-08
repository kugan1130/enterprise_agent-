"""Central Redis client initialization."""

from functools import lru_cache
import redis

from backend.app.core.config import settings


@lru_cache
def get_redis_client() -> redis.Redis:
    """
    Returns a shared Redis client instance using settings.REDIS_URL.
    """
    return redis.from_url(settings.REDIS_URL, decode_responses=True)
