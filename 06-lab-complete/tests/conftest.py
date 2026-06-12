"""Pytest fixtures — set env before app imports."""
import os

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("AGENT_API_KEY", "ci-test-api-key")
os.environ.setdefault("JWT_SECRET", "ci-test-jwt-secret")
# REDIS_URL unset locally → fakeredis; CI sets redis://127.0.0.1:6379/0

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.redis_client import close_redis


@pytest.fixture
def client():
    close_redis()
    with TestClient(app) as test_client:
        yield test_client
    close_redis()


@pytest.fixture
def api_headers():
    return {"X-API-Key": os.environ["AGENT_API_KEY"]}
