"""Daily position review agent endpoints.

Provides routes for triggering daily reviews, listing available dates,
fetching reviews by date, and health checks.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_agent_task_service, get_current_user, get_db, get_llm_service
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.core.rate_limit import check_llm_rate_limit
from app.schemas.daily_position_review import (
    DailyReviewDateListResponse,
    DailyReviewHealthResponse,
    DailyReviewRequest,
    DailyReviewResponse,
)
from app.services.agent_services import AgentTaskService
from app.services.llm_service import LLMService

router = APIRouter(prefix="/daily-position-review", tags=["daily-position-review"])
AGENT_NAME = "daily_review"
logger = logging.getLogger(__name__)


def _row_to_response(row: dict) -> DailyReviewResponse:
    """Convert a database row to a DailyReviewResponse."""
    review_output = row.get("review_output")
    if isinstance(review_output, str):
        try:
            review_output = json.loads(review_output)
        except (json.JSONDecodeError, TypeError):
            pass

    metadata = row.get("metadata")
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except (json.JSONDecodeError, TypeError):
            pass

    evidence_summary = row.get("evidence_summary")
    if isinstance(evidence_summary, str):
        try:
            evidence_summary = json.loads(evidence_summary)
        except (json.JSONDecodeError, TypeError):
            pass

    run_trace = row.get("run_trace")
    if isinstance(run_trace, str):
        try:
            run_trace = json.loads(run_trace)
        except (json.JSONDecodeError, TypeError):
            pass

    return DailyReviewResponse(
        id=row["id"],
        report_date=row["report_date"],
        review_output=review_output,
        metadata=metadata,
        evidence_summary=evidence_summary,
        run_trace=run_trace,
        created_at=row.get("created_at"),
    )


@router.post("/generate", response_model=DailyReviewResponse)
def generate_daily_review(
    request: DailyReviewRequest,
    llm_service: LLMService = Depends(get_llm_service),
    task_service: AgentTaskService = Depends(get_agent_task_service),
    _user: str | None = Depends(get_current_user),
    _rate: None = Depends(check_llm_rate_limit),
) -> DailyReviewResponse:
    """Trigger a daily position review synchronously and return the result."""
    db = task_service.db

    try:
        from app.agents.daily_review.agent import generate_daily_review as run_review
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                run_review(db, llm_service, request.report_date)
            )
        finally:
            loop.close()
    except Exception as exc:
        logger.exception("Daily review generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Daily review generation failed: {str(exc)[:300]}",
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No data available for the requested date",
        )

    return _row_to_response(result) if isinstance(result, dict) else DailyReviewResponse(
        id="",
        report_date=request.report_date,
        review_output=str(result),
    )


@router.get("/dates", response_model=DailyReviewDateListResponse)
def list_review_dates(
    limit: int = Query(default=60, ge=1, le=500),
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> DailyReviewDateListResponse:
    """List dates that have daily position reviews."""
    rows = db.execute(
        "SELECT DISTINCT report_date FROM daily_position_reviews "
        "ORDER BY report_date DESC LIMIT ?",
        (limit,),
    )
    dates = [row["report_date"] for row in rows]
    return DailyReviewDateListResponse(items=dates)


@router.get("/reviews/{date}", response_model=DailyReviewResponse)
def get_review_by_date(
    date: str,
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> DailyReviewResponse:
    """Get the daily position review for a specific date."""
    row = db.execute_one(
        "SELECT * FROM daily_position_reviews WHERE report_date = ? ORDER BY created_at DESC LIMIT 1",
        (date,),
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No daily position review found for date: {date}",
        )
    return _row_to_response(row)


@router.get("/health", response_model=DailyReviewHealthResponse)
def health_check(
    settings: Settings = Depends(get_settings),
    _user: str | None = Depends(get_current_user),
) -> DailyReviewHealthResponse:
    """Check daily review agent health."""
    return DailyReviewHealthResponse(
        status="ok",
        agent_name=AGENT_NAME,
        llm_configured=bool(settings.llm_api_key),
        message="Daily review agent is available",
    )
