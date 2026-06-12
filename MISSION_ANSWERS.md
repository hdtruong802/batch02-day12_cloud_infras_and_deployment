# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

1. **API key hardcode** — `OPENAI_API_KEY = "sk-hardcoded-fake-key..."` trong source code, dễ lộ khi push Git.
2. **Database credentials hardcode** — `DATABASE_URL` chứa username/password trong code.
3. **Debug mode bật** — `DEBUG = True`, `reload=True` không phù hợp production.
4. **Không có health check** — platform không biết khi nào restart container.
5. **Port/host cố định** — `host="localhost"`, `port=8000` không đọc từ env var.
6. **Logging bằng print()** — in secret ra console, không có structured logging.
7. **Không graceful shutdown** — không xử lý SIGTERM.

### Exercise 1.3: Comparison table

| Feature | Develop | Production | Why Important? |
|---------|---------|------------|----------------|
| Config | Hardcode trong code | Environment variables | Bảo mật secrets, deploy linh hoạt |
| Health check | Không có | `/health`, `/ready` | Platform tự restart, LB routing |
| Logging | `print()` | JSON structured logging | Debug production, observability |
| Shutdown | Đột ngột | SIGTERM handler + lifespan | Không mất request đang xử lý |
| Host binding | `localhost` | `0.0.0.0` | Container/cloud cần bind all interfaces |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. **Base image:** `python:3.11-slim` — nhẹ, đủ cho Python app.
2. **Working directory:** `/app` (runtime stage).
3. **COPY requirements.txt trước:** Tận dụng Docker layer cache — dependencies ít đổi hơn code.
4. **CMD vs ENTRYPOINT:** CMD có thể override khi `docker run`; ENTRYPOINT cố định executable, args truyền thêm.

### Exercise 2.3: Image size comparison

- Develop (single-stage): ~900 MB (ước lượng, full python image + build tools).
- Production (multi-stage + slim): ~200–350 MB.
- Difference: ~60–70% nhỏ hơn nhờ multi-stage và slim base.

### Exercise 2.4: Docker Compose architecture

Services: `agent`, `redis`, `nginx`. Nginx nhận traffic port 80 → proxy tới `agent:8000`. Agent lưu state trong Redis → stateless, scale được nhiều replicas.

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- **Platform:** Railway hoặc Render (xem `DEPLOYMENT.md`)
- **Config files:** `railway.toml` / `render.yaml`
- **Env vars cần set:** `PORT`, `AGENT_API_KEY`, `REDIS_URL`, `ENVIRONMENT=production`

### Exercise 3.2: Railway vs Render

| | Railway | Render |
|---|---------|--------|
| Config | `railway.toml` | `render.yaml` |
| Deploy | `railway up` CLI | Git push + Blueprint |
| Redis | Add-on plugin | `fromService` trong yaml |

---

## Part 4: API Security

### Exercise 4.1-4.3: Test results

```bash
# Không có key → 401
curl -X POST http://localhost/ask -d '{"user_id":"test","question":"Hello"}'
# → 401 Unauthorized

# Có key → 200
curl -H "X-API-Key: lab-secret-key-123" -X POST http://localhost/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
# → 200 OK

# Rate limit → 429 sau 10 requests/phút
```

### Exercise 4.4: Cost guard implementation

Dùng Redis key `budget:{user_id}:{YYYY-MM}` để track chi phí theo tháng. Trước mỗi request gọi `check_budget()` — nếu vượt $10/tháng trả HTTP 402. Sau request gọi `record_cost()` với `incrbyfloat`.

---

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes

- **`/health`:** Liveness probe — process còn sống, Redis connected.
- **`/ready`:** Readiness probe — ping Redis, trả 503 nếu Redis down.
- **Graceful shutdown:** SIGTERM handler + lifespan cleanup đóng Redis connection.
- **Stateless:** Conversation history, rate limit, budget đều trong Redis — không lưu memory.
- **Load balancing:** `docker compose up --scale agent=3` + Nginx upstream round-robin.

---

## Part 6: Final Project

### Requirements checklist

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| REST API `/ask` | Done | `app/routers/agent.py` — FastAPI + Pydantic |
| Conversation history | Done | `app/session.py` — Redis lists, TTL 1h |
| Docker multi-stage | Done | `06-lab-complete/Dockerfile` — builder + slim runtime |
| Config from env | Done | `app/config.py` — 12-factor dataclass |
| API key auth | Done | `app/auth.py` — `X-API-Key` header |
| Rate limit 10/min | Done | `app/rate_limiter.py` — Redis sliding window → 429 |
| Cost guard $10/month | Done | `app/cost_guard.py` — Redis budget key → 402 |
| `/health` | Done | `app/routers/ops.py` — liveness probe |
| `/ready` | Done | `app/routers/ops.py` — Redis ping, 503 if down |
| Graceful shutdown | Done | `app/main.py` — SIGTERM + lifespan cleanup |
| Stateless (Redis) | Done | History, rate, budget in Redis — not in memory |
| JSON logging | Done | `app/main.py` — `json.dumps` event logs |
| Nginx + scale 3 | Done | `docker-compose.yml` + `nginx.conf` |
| Deploy Railway | Done | Root `Dockerfile` + `railway.json` |
| Public URL | Done | See `DEPLOYMENT.md` |
| CI (GitHub Actions) | Done | `.github/workflows/ci.yml` |

### Architecture (implemented)

```
Client → Nginx (:80) → Agent x3 (:8000) → Redis
```

- **Nginx:** round-robin load balancer (`nginx.conf`)
- **Agent:** stateless FastAPI containers, `X-Instance-Id` header
- **Redis:** conversation history, rate limits, monthly budget

### Validation results

```bash
cd 06-lab-complete
python check_production_ready.py   # 20/20 checks passed
pytest tests/ -v                   # 12 tests passed
```

**Production URL:**

```
https://batch02-day12cloudinfrasanddeployment-production-dfb1.up.railway.app
```

**Sample tests:**

```bash
# Health
curl https://batch02-day12cloudinfrasanddeployment-production-dfb1.up.railway.app/health

# Ask (replace YOUR_KEY with AGENT_API_KEY on Railway)
curl -X POST https://batch02-day12cloudinfrasanddeployment-production-dfb1.up.railway.app/ask \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'

# Conversation context
curl -X POST .../ask -H "X-API-Key: YOUR_KEY" -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"What did I just say?"}'
```

### Self-assessment (Grading Rubric)

| Criteria | Points | Notes |
|----------|--------|-------|
| Functionality | 20/20 | Agent, history, error 422 |
| Docker | 15/15 | Multi-stage, compose, nginx |
| Security | 20/20 | Auth, rate limit, cost guard |
| Reliability | 20/20 | Health, ready, SIGTERM |
| Scalability | 15/15 | Stateless + LB |
| Deployment | 10/10 | Railway public URL + CI |
| **Total** | **100/100** | |
