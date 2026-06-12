"""
FastAPI Production AI Agent — Day 12 Lab Complete
"""
import signal
import logging
import json
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app import state
from app.config import settings
from app.redis_client import close_redis, get_redis
from app.routers import agent, ops

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(json.dumps({
        "event": "startup",
        "framework": "FastAPI",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "instance_id": state.instance_id,
    }))
    try:
        get_redis().ping()
        state.is_ready = True
        logger.info(json.dumps({"event": "ready", "redis": True}))
    except Exception as exc:
        logger.error(json.dumps({"event": "startup_failed", "error": str(exc)}))
        state.is_ready = False

    yield

    state.is_ready = False
    close_redis()
    logger.info(json.dumps({"event": "shutdown", "instance_id": state.instance_id}))


def create_app() -> FastAPI:
    """FastAPI application factory."""
    application = FastAPI(
        title=settings.app_name,
        description="Production AI Agent API — FastAPI + Redis + Docker",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )

    @application.middleware("http")
    async def request_middleware(request: Request, call_next):
        state.request_count += 1
        start = time.time()
        try:
            response: Response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-Instance-Id"] = state.instance_id
            response.headers["X-Powered-By"] = "FastAPI"
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
            state.error_count += 1
            raise

    application.include_router(agent.router)
    application.include_router(ops.router)

    @application.get("/", tags=["Info"], summary="API info")
    def root():
        return {
            "framework": "FastAPI",
            "app": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "instance_id": state.instance_id,
            "docs": "/docs",
            "openapi": "/openapi.json",
            "endpoints": {
                "ask": "POST /ask (requires X-API-Key)",
                "health": "GET /health",
                "ready": "GET /ready",
                "history": "GET /history/{user_id}",
            },
        }

    return application


app = create_app()


def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


if __name__ == "__main__":
    logger.info(json.dumps({
        "event": "boot",
        "framework": "FastAPI",
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
