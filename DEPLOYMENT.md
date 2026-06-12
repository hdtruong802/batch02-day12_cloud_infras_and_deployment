# Deployment Information

## Local Stack (verified)

Chạy full stack local với Docker Compose:

```bash
cd 06-lab-complete
docker compose up --build --scale agent=3
```

## Public URL

```
https://batch02-day12cloudinfrasanddeployment-production-dfb1.up.railway.app
```

## Platform

Railway

## Deploy Railway

```bash
# Từ repo root (monorepo)
npm i -g @railway/cli
railway login
railway link -p <project-id> -s batch02-day12_cloud_infras_and_deployment

# Biến bắt buộc — dùng PRIVATE Redis URL (không dùng REDIS_PUBLIC_URL)
railway variable set AGENT_API_KEY=<strong-random-key>
railway variable set JWT_SECRET=<strong-random-secret>
railway variable set ENVIRONMENT=production
railway variable set 'REDIS_URL=${{Redis.REDIS_URL}}'   # private network, no egress fee

railway up
railway domain
```

> **Lưu ý Redis:** Trên Railway Dashboard, reference `${{Redis.REDIS_URL}}` (private).
> Không set `REDIS_PUBLIC_URL` trên agent service — gây egress fee warning.

## Deploy Render

1. Push repo lên GitHub
2. Render Dashboard → New → Blueprint
3. Connect repo → Render đọc `06-lab-complete/render.yaml`
4. Set `REDIS_URL`, `OPENAI_API_KEY` (optional)
5. Deploy

## Test Commands

### Health Check

```bash
curl http://localhost/health
# Expected: {"status":"ok",...}
```

### Readiness

```bash
curl http://localhost/ready
# Expected: {"ready":true,...}
```

### API Test (with authentication)

```bash
# Thay YOUR_KEY bằng AGENT_API_KEY trên Railway
curl -X POST https://batch02-day12cloudinfrasanddeployment-production-dfb1.up.railway.app/ask \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "question": "Hello"}'
```

### Conversation history

```bash
curl -X POST http://localhost/ask \
  -H "X-API-Key: lab-secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "question": "What did I just say?"}'
```

### Rate limit test

```powershell
1..15 | ForEach-Object {
  curl.exe -s -o NUL -w "%{http_code}`n" -X POST http://localhost/ask `
    -H "X-API-Key: lab-secret-key-123" `
    -H "Content-Type: application/json" `
    -d '{"user_id":"ratetest","question":"test"}'
}
# Expect 429 after 10 requests
```

## Environment Variables Set

| Variable | Description |
|----------|-------------|
| `PORT` | Server port (cloud injects) |
| `REDIS_URL` | Redis connection string |
| `AGENT_API_KEY` | API authentication key |
| `RATE_LIMIT_PER_MINUTE` | Default: 10 |
| `MONTHLY_BUDGET_USD` | Default: 10.0 |
| `LOG_LEVEL` | Default: INFO |
| `ENVIRONMENT` | `production` on cloud |

## Production Readiness Check

```bash
cd 06-lab-complete
python check_production_ready.py
```
