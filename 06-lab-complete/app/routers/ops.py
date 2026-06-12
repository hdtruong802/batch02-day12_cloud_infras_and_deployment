"""Operations routes — health, readiness, metrics."""
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app import state
from app.auth import verify_api_key
from app.config import settings
from app.redis_client import is_redis_fallback, ping_redis
from app.schemas import HealthResponse, MetricsResponse, ReadyResponse

router = APIRouter(tags=["Operations"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
)
def health():
    redis_ok = ping_redis()
    return HealthResponse(
        status="ok" if redis_ok else "degraded",
        version=settings.app_version,
        environment=settings.environment,
        instance_id=state.instance_id,
        uptime_seconds=round(time.time() - state.start_time, 1),
        total_requests=state.request_count,
        redis_connected=redis_ok,
        redis_mode="memory" if is_redis_fallback() else "redis",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Readiness probe",
)
def ready():
    if not state.is_ready or not ping_redis():
        raise HTTPException(503, "Not ready — Redis unavailable")
    return ReadyResponse(ready=True, instance=state.instance_id)


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Protected metrics",
)
def metrics(_key: str = Depends(verify_api_key)):
    return MetricsResponse(
        uptime_seconds=round(time.time() - state.start_time, 1),
        total_requests=state.request_count,
        error_count=state.error_count,
        instance_id=state.instance_id,
        rate_limit_per_minute=settings.rate_limit_per_minute,
        monthly_budget_usd=settings.monthly_budget_usd,
    )
