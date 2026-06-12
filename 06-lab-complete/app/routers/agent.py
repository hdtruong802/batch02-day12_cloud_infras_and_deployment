"""Agent API routes — FastAPI router."""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from app import state
from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, estimate_cost, record_cost
from app.rate_limiter import check_rate_limit
from app.schemas import AskRequest, AskResponse, HistoryResponse
from app.session import append_message, clear_history, get_history
from utils.mock_llm import ask as llm_ask

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Agent"])


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask the AI agent",
    description="Send a question. Requires `X-API-Key` header.",
)
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
    record_cost(body.user_id, estimate_cost(input_tokens, output_tokens))

    user_history = get_history(body.user_id)
    turn = len([m for m in user_history if m["role"] == "user"])

    return AskResponse(
        user_id=body.user_id,
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        turn=turn,
        served_by=state.instance_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/history/{user_id}",
    response_model=HistoryResponse,
    summary="Get conversation history",
)
def history(user_id: str, _key: str = Depends(verify_api_key)):
    messages = get_history(user_id)
    return HistoryResponse(user_id=user_id, messages=messages, count=len(messages))


@router.delete("/history/{user_id}", summary="Clear conversation history")
def delete_history(user_id: str, _key: str = Depends(verify_api_key)):
    clear_history(user_id)
    return {"deleted": user_id}
