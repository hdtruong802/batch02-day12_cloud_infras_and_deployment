"""
Production AI Agent — Day 12 Lab Complete

Combines: 12-factor config, Docker, API security, Redis statelessness,
health/readiness probes, graceful shutdown, structured JSON logging.
"""
import os
import time
import signal
import logging
import json
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.config import settings
from app.auth import verify_api_key
from app.rate_limiter import check_rate_limit
from app.cost_guard import check_budget, record_cost, estimate_cost
from app.session import append_message, get_history, clear_history
from app.redis_client import ping_redis, close_redis, get_redis, is_redis_fallback
from utils.mock_llm import ask as llm_ask

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0
INSTANCE_ID = os.getenv("INSTANCE_ID", f"instance-{uuid.uuid4().hex[:6]}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "instance_id": INSTANCE_ID,
    }))
    try:
        get_redis().ping()
        _is_ready = True
        logger.info(json.dumps({"event": "ready", "redis": True}))
    except Exception as exc:
        logger.error(json.dumps({"event": "startup_failed", "error": str(exc)}))
        _is_ready = False

    yield

    _is_ready = False
    close_redis()
    logger.info(json.dumps({"event": "shutdown", "instance_id": INSTANCE_ID}))


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    start = time.time()
    _request_count += 1
    try:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Instance-Id"] = INSTANCE_ID
        if "server" in response.headers:
            del response.headers["server"]
        duration = round((time.time() - start) * 1000, 1)
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": duration,
        }))
        return response
    except Exception:
        _error_count += 1
        raise


class AskRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    user_id: str
    question: str
    answer: str
    model: str
    turn: int
    served_by: str
    timestamp: str


@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "instance_id": INSTANCE_ID,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
            "history": "GET /history/{user_id}",
        },
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    _key: str = Depends(verify_api_key),
):
    check_rate_limit(body.user_id)

    input_tokens = len(body.question.split()) * 2
    estimated = estimate_cost(input_tokens, 0)
    check_budget(body.user_id, estimated)

    logger.info(json.dumps({
        "event": "agent_call",
        "user_id": body.user_id,
        "q_len": len(body.question),
        "client": str(request.client.host) if request.client else "unknown",
    }))

    history = get_history(body.user_id)
    append_message(body.user_id, "user", body.question)

    if history and "what did" in body.question.lower():
        answer = "Bạn vừa nói: " + history[-1]["content"]
    else:
        answer = llm_ask(body.question)

    append_message(body.user_id, "assistant", answer)

    output_tokens = len(answer.split()) * 2
    total_cost = estimate_cost(input_tokens, output_tokens)
    record_cost(body.user_id, total_cost)

    user_history = get_history(body.user_id)
    turn = len([m for m in user_history if m["role"] == "user"])

    return AskResponse(
        user_id=body.user_id,
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        turn=turn,
        served_by=INSTANCE_ID,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/history/{user_id}", tags=["Agent"])
def history(user_id: str, _key: str = Depends(verify_api_key)):
    messages = get_history(user_id)
    return {"user_id": user_id, "messages": messages, "count": len(messages)}


@app.delete("/history/{user_id}", tags=["Agent"])
def delete_history(user_id: str, _key: str = Depends(verify_api_key)):
    clear_history(user_id)
    return {"deleted": user_id}


@app.get("/health", tags=["Operations"])
def health():
    redis_ok = ping_redis()
    status = "ok" if redis_ok else "degraded"
    return {
        "status": status,
        "version": settings.app_version,
        "environment": settings.environment,
        "instance_id": INSTANCE_ID,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "redis_connected": redis_ok,
        "redis_mode": "memory" if is_redis_fallback() else "redis",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    if not _is_ready or not ping_redis():
        raise HTTPException(503, "Not ready — Redis unavailable")
    return {"ready": True, "instance": INSTANCE_ID}


@app.get("/metrics", tags=["Operations"])
def metrics(_key: str = Depends(verify_api_key)):
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "instance_id": INSTANCE_ID,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
        "monthly_budget_usd": settings.monthly_budget_usd,
    }


def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


if __name__ == "__main__":
    logger.info(json.dumps({
        "event": "boot",
        "app": settings.app_name,
        "host": settings.host,
        "port": settings.port,
    }))
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
