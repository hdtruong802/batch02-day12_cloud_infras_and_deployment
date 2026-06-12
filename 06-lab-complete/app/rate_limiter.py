"""Redis-backed sliding window rate limiter."""
import time

from fastapi import HTTPException

from app.config import settings
from app.redis_client import get_redis


def check_rate_limit(user_id: str) -> None:
    """
    Sliding window rate limit per user_id.
    Raises HTTP 429 when limit exceeded.
    """
    r = get_redis()
    now = time.time()
    window = 60
    key = f"rate:{user_id}"

    r.zremrangebyscore(key, 0, now - window)
    current = r.zcard(key)

    if current >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": settings.rate_limit_per_minute,
                "window_seconds": window,
            },
            headers={"Retry-After": "60"},
        )

    r.zadd(key, {str(now): now})
    r.expire(key, window)
