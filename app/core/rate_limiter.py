"""Simple Redis-backed rate limiter."""

from fastapi import HTTPException, Request, status

from app.config import get_settings

settings = get_settings()

_memory_buckets: dict[str, list[float]] = {}


async def rate_limit(request: Request, limit: int | None = None) -> None:
    """In-memory sliding window (works without Redis for MVP; Redis used by Celery)."""
    import time

    limit = limit or settings.RATE_LIMIT_PER_MINUTE
    client = request.client.host if request.client else "unknown"
    key = f"{client}:{request.url.path}"
    now = time.time()
    window = 60.0

    bucket = _memory_buckets.setdefault(key, [])
    _memory_buckets[key] = [t for t in bucket if now - t < window]
    if len(_memory_buckets[key]) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )
    _memory_buckets[key].append(now)
