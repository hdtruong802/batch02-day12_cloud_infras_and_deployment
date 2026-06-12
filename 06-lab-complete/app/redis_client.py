"""Shared Redis connection with in-memory fallback only when Redis is not configured."""
import json
import logging

import redis

from app.config import settings

logger = logging.getLogger(__name__)
_client: redis.Redis | None = None
_using_fallback = False

_LOCAL_DEFAULTS = {"redis://localhost:6379/0", "redis://localhost:6379", ""}


def _redis_configured() -> bool:
    return settings.redis_url.strip() not in _LOCAL_DEFAULTS and bool(settings.redis_url.strip())


def get_redis() -> redis.Redis:
    global _client, _using_fallback
    if _client is None:
        if not _redis_configured():
            import fakeredis

            logger.info(json.dumps({"event": "redis_fallback", "reason": "not_configured"}))
            _client = fakeredis.FakeRedis(decode_responses=True)
            _using_fallback = True
        else:
            try:
                _client = redis.from_url(settings.redis_url, decode_responses=True)
                _client.ping()
                _using_fallback = False
                logger.info(json.dumps({"event": "redis_connected", "mode": "redis"}))
            except Exception as exc:
                if settings.environment == "production":
                    logger.error("Redis connection failed in production: %s", exc)
                    raise
                import fakeredis

                logger.warning(json.dumps({"event": "redis_fallback", "error": str(exc)}))
                _client = fakeredis.FakeRedis(decode_responses=True)
                _using_fallback = True
    return _client


def ping_redis() -> bool:
    try:
        get_redis().ping()
        return not _using_fallback
    except Exception:
        return False


def is_redis_fallback() -> bool:
    get_redis()
    return _using_fallback


def close_redis() -> None:
    global _client, _using_fallback
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
        _client = None
        _using_fallback = False
