# Lab 12 — Complete Production Agent

Production-ready AI agent kết hợp tất cả Day 12 concepts.

## Checklist Deliverable

- [x] Dockerfile (multi-stage, non-root, HEALTHCHECK)
- [x] docker-compose.yml (agent + redis + nginx)
- [x] `.dockerignore`, `.env.example`
- [x] `GET /health` — liveness probe
- [x] `GET /ready` — readiness probe (Redis ping)
- [x] API Key authentication (`X-API-Key`)
- [x] Rate limiting (10 req/min per user, Redis)
- [x] Cost guard ($10/month per user, Redis)
- [x] Config từ environment variables
- [x] Structured JSON logging
- [x] Graceful shutdown (SIGTERM)
- [x] Stateless design (conversation history in Redis)
- [x] `railway.toml` + `render.yaml`

## Cấu Trúc

```
06-lab-complete/
├── app/
│   ├── main.py              # FastAPI factory + middleware
│   ├── config.py            # 12-factor settings
│   ├── auth.py              # API Key auth
│   ├── rate_limiter.py      # Redis sliding window
│   ├── cost_guard.py        # Monthly budget
│   ├── session.py           # Conversation history
│   ├── redis_client.py      # Redis + fakeredis fallback
│   ├── schemas.py           # Pydantic models
│   ├── state.py             # Runtime counters
│   └── routers/
│       ├── agent.py         # POST /ask, GET /history
│       └── ops.py           # /health, /ready, /metrics
├── utils/
│   └── mock_llm.py
├── tests/
│   ├── conftest.py
│   └── test_api.py
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── railway.toml
├── render.yaml
└── check_production_ready.py
```

## Chạy Local

```bash
# 1. Setup env
cp .env.example .env.local
# Sửa AGENT_API_KEY trong .env.local

# 2. Docker Compose (cần Docker Desktop đang chạy)
docker compose up --build --scale agent=3

# 3. Test
curl http://localhost/health
curl -H "X-API-Key: lab-secret-key-123" \
     -X POST http://localhost/ask \
     -H "Content-Type: application/json" \
     -d '{"user_id": "user1", "question": "What is deployment?"}'
```

## Kiểm Tra

```bash
python check_production_ready.py
# Expected: 20/20 checks passed
```

## Deploy

Xem [DEPLOYMENT.md](../DEPLOYMENT.md) ở thư mục gốc repo.
