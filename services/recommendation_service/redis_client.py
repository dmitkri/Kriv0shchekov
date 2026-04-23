from typing import Optional

from redis.asyncio import Redis, from_url

from services.recommendation_service.config import settings

_redis: Optional[Redis] = None


async def connect_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = from_url(settings.REDIS_URL, decode_responses=True)
        await _redis.ping()
    return _redis


def get_redis() -> Redis:
    if _redis is None:
        raise RuntimeError("Redis is not connected")
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None

