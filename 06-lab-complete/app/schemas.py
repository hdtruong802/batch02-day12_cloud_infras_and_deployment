"""FastAPI Pydantic schemas."""
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64, examples=["user1"])
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        examples=["What is deployment?"],
    )


class AskResponse(BaseModel):
    user_id: str
    question: str
    answer: str
    model: str
    turn: int
    served_by: str
    timestamp: str


class HistoryResponse(BaseModel):
    user_id: str
    messages: list[dict]
    count: int


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    instance_id: str
    uptime_seconds: float
    total_requests: int
    redis_connected: bool
    redis_mode: str
    framework: str = "FastAPI"
    timestamp: str


class ReadyResponse(BaseModel):
    ready: bool
    instance: str


class MetricsResponse(BaseModel):
    uptime_seconds: float
    total_requests: int
    error_count: int
    instance_id: str
    rate_limit_per_minute: int
    monthly_budget_usd: float
    framework: str = "FastAPI"
