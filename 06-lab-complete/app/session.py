"""Redis-backed conversation history (stateless design)."""
import json
from datetime import datetime, timezone

from app.redis_client import get_redis

HISTORY_TTL = 3600
MAX_MESSAGES = 20


def get_history(user_id: str) -> list[dict]:
    r = get_redis()
    raw = r.lrange(f"history:{user_id}", 0, -1)
    return [json.loads(item) for item in raw]


def append_message(user_id: str, role: str, content: str) -> list[dict]:
    r = get_redis()
    key = f"history:{user_id}"
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    r.rpush(key, json.dumps(message))
    r.ltrim(key, -MAX_MESSAGES, -1)
    r.expire(key, HISTORY_TTL)
    return get_history(user_id)


def clear_history(user_id: str) -> None:
    get_redis().delete(f"history:{user_id}")
