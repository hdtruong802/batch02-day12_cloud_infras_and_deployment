# Railway root Dockerfile — builds 06-lab-complete production agent
# Required because Railway deploys from monorepo root (not subdirectory)

FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y gcc \
    && rm -rf /var/lib/apt/lists/*

COPY 06-lab-complete/requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt


FROM python:3.11-slim AS runtime

RUN groupadd -r agent && useradd -r -g agent -d /app agent

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY 06-lab-complete/app/ ./app/
COPY 06-lab-complete/utils/ ./utils/

RUN chown -R agent:agent /app

USER agent

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/health')" \
    || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
