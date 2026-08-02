"""Redis-backed sliding-window rate limiter with in-memory fallback."""

from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import HTTPException, Request, status

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

_memory_buckets: dict[str, list[float]] = {}
_redis = None
_redis_failed = False


def _get_redis():
    global _redis, _redis_failed
    if _redis_failed:
        return None
    if _redis is not None:
        return _redis
    try:
        import redis

        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1)
        _redis.ping()
        return _redis
    except Exception:
        logger.warning("Redis unavailable for rate limiting; using in-memory fallback")
        _redis_failed = True
        return None


async def rate_limit(request: Request, limit: Optional[int] = None) -> None:
    limit = limit or settings.RATE_LIMIT_PER_MINUTE
    client = request.client.host if request.client else "unknown"
    key = f"rl:{client}:{request.url.path}"
    now = time.time()
    window = 60.0

    r = _get_redis()
    if r is not None:
        try:
            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, int(window) + 1)
            results = pipe.execute()
            count = results[2]
            if count > limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Try again later.",
                )
            return
        except HTTPException:
            raise
        except Exception:
            logger.exception("Redis rate limit error; falling back to memory")

    bucket = _memory_buckets.setdefault(key, [])
    _memory_buckets[key] = [t for t in bucket if now - t < window]
    if len(_memory_buckets[key]) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )
    _memory_buckets[key].append(now)
