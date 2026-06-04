"""Trade review agent endpoints.

Provides routes for triggering trade reviews, listing recent reviews,
fetching reviews by ID, and health checks.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_agent_task_service, get_current_user, get_db, get_llm_service
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.core.rate_limit import check_llm_rate_limit
from app.schemas.trade_review import (
    TradeReviewHealthResponse,
    TradeReviewListResponse,
    TradeReviewRequest,
    TradeReviewResponse,
)
from app.services.agent_services import AgentTaskService
from app.services.llm_service import LLMService
from app.utils.json_fields import parse_json_fields

router = APIRouter(prefix="/trade-review", tags=["trade-review-agent"])
AGENT_NAME = "trade_review"
logger = logging.getLogger(__name__)


def _row_to_response(row: dict) -> TradeReviewResponse:
    """Convert a database row to a TradeReviewResponse."""
    row = parse_json_fields(row, ["review_output", "metadata", "evidence_summary", "run_trace"])
    return TradeReviewResponse(**{k: row.get(k) for k in row if k in TradeReviewResponse.model_fields})


@router.post("/review", response_model=TradeReviewResponse)
async def trigger_trade_review(
    request: TradeReviewRequest,
    llm_service: LLMService = Depends(get_llm_service),
    task_service: AgentTaskService = Depends(get_agent_task_service),
    _user: str | None = Depends(get_current_user),
    _rate: None = Depends(check_llm_rate_limit),
) -> TradeReviewResponse:
    """Trigger a trade review and return the result."""
    db = task_service.db

    try:
        from app.agents.trade_review.agent import review_trade

        result = await review_trade(
            db, llm_service, request.symbol,
            trade_id=request.trade_id,
            start_date=request.start_date,
            end_date=request.end_date,
        )
    except Exception as exc:
        logger.exception("Trade review failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trade review failed: {str(exc)[:300]}",
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No data available for the requested review",
        )

    return _row_to_response(result) if isinstance(result, dict) else TradeReviewResponse(
        id="",
        review_type="trade_review",
        symbol=request.symbol,
        review_output=str(result),
    )


@router.get("/reviews", response_model=TradeReviewListResponse)
def list_reviews(
    limit: int = Query(default=20, ge=1, le=100),
    symbol: str | None = Query(default=None),
    review_type: str | None = Query(default=None),
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> TradeReviewListResponse:
    """List recent trade reviews with optional filters."""
    conditions = []
    params: list = []

    if symbol:
        conditions.append("symbol = ?")
        params.append(symbol)
    if review_type:
        conditions.append("review_type = ?")
        params.append(review_type)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM trade_reviews {where} ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = db.execute(sql, tuple(params))
    items = [_row_to_response(row) for row in rows]
    return TradeReviewListResponse(items=items)


@router.get("/reviews/{review_id}", response_model=TradeReviewResponse)
def get_review_by_id(
    review_id: str,
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> TradeReviewResponse:
    """Get a specific trade review by ID."""
    row = db.execute_one(
        "SELECT * FROM trade_reviews WHERE id = ?",
        (review_id,),
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trade review not found: {review_id}",
        )
    return _row_to_response(row)


@router.get("/health", response_model=TradeReviewHealthResponse)
def health_check(
    settings: Settings = Depends(get_settings),
    _user: str | None = Depends(get_current_user),
) -> TradeReviewHealthResponse:
    """Check trade review agent health."""
    return TradeReviewHealthResponse(
        status="ok",
        agent_name=AGENT_NAME,
        llm_configured=bool(settings.llm_api_key),
        message="Trade review agent is available",
    )
