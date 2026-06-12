"""API integration tests — run in CI before deploy."""
import pytest


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["framework"] == "FastAPI"
    assert "endpoints" in data


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["framework"] == "FastAPI"
    assert "instance_id" in data


def test_ready(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["ready"] is True


def test_openapi_docs(client):
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200


def test_ask_requires_api_key(client):
    response = client.post("/ask", json={"user_id": "u1", "question": "Hello"})
    assert response.status_code in (401, 403)


def test_ask_success(client, api_headers):
    response = client.post(
        "/ask",
        headers=api_headers,
        json={"user_id": "ci-user", "question": "What is FastAPI?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "ci-user"
    assert data["question"] == "What is FastAPI?"
    assert data["answer"]
    assert data["turn"] >= 1


def test_history(client, api_headers):
    client.post(
        "/ask",
        headers=api_headers,
        json={"user_id": "hist-user", "question": "First message"},
    )
    response = client.get("/history/hist-user", headers=api_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "hist-user"
    assert data["count"] >= 2


def test_metrics_requires_api_key(client):
    assert client.get("/metrics").status_code in (401, 403)


def test_metrics_success(client, api_headers):
    response = client.get("/metrics", headers=api_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["framework"] == "FastAPI"
    assert "total_requests" in data
