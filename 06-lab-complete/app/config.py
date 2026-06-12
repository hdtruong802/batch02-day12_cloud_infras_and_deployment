"""Production config — 12-Factor: tất cả từ environment variables."""
import os
import logging
from dataclasses import dataclass, field


def _resolve_redis_url() -> str:
    """Resolve Redis URL from REDIS_URL or Railway individual vars (private network)."""
    url = os.getenv("REDIS_URL", "").strip()
    if url:
        return url

    host = os.getenv("REDISHOST", "").strip()
    if not host:
        return "redis://localhost:6379/0"

    port = os.getenv("REDISPORT", "6379").strip()
    user = os.getenv("REDISUSER", "default").strip()
    password = os.getenv("REDISPASSWORD") or os.getenv("REDIS_PASSWORD") or ""

    if password:
        return f"redis://{user}:{password}@{host}:{port}"
    return f"redis://{host}:{port}"


@dataclass
class Settings:
    # Server
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # App
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "Production AI Agent"))
    app_version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "1.0.0"))

    # LLM
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))

    # Security
    agent_api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", "dev-key-change-me"))
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", ""))
    allowed_origins: list = field(
        default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "*").split(",")
    )

    # Rate limiting
    rate_limit_per_minute: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    )

    # Budget
    monthly_budget_usd: float = field(
        default_factory=lambda: float(os.getenv("MONTHLY_BUDGET_USD", "10.0"))
    )

    # Storage — prefer private REDIS_URL (never REDIS_PUBLIC_URL on Railway)
    redis_url: str = field(default_factory=_resolve_redis_url)

    def validate(self):
        logger = logging.getLogger(__name__)

        weak_keys = {
            "dev-key-change-me",
            "dev-key-change-me-in-production",
            "lab-secret-key-123",
        }
        if self.environment == "production" and self.agent_api_key in weak_keys:
            logger.warning(
                "AGENT_API_KEY looks like a default/lab value — set a strong secret in Railway variables"
            )

        if self.environment == "production" and not self.openai_api_key:
            logger.info("Using mock LLM (OPENAI_API_KEY not set — expected for Day 12 lab)")

        return self


settings = Settings().validate()
