"""Daily position review agent endpoints.

Provides routes for triggering daily reviews, listing available dates,
fetching reviews by date, and health checks.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_agent_task_service, get_current_user, get_db, get_llm_service, get_prompt_service
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.core.rate_limit import check_llm_rate_limit
from app.schemas.daily_position_review import (
    DailyReviewDateListResponse,
    DailyReviewHealthResponse,
    DailyReviewRequest,
    DailyReviewResponse,
)
from app.services.agent_services import AgentTaskService, extract_trace_metrics
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService
from app.utils.json_fields import parse_json_fields

router = APIRouter(prefix="/daily-position-review", tags=["daily-position-review"])
AGENT_NAME = "daily_review"
logger = logging.getLogger(__name__)


def _row_to_response(row: dict) -> DailyReviewResponse:
    """Convert a database row to a DailyReviewResponse.

    Flattens review_output fields into the top-level response so the frontend
    can access summary, account_conclusion, market_context, etc. directly.
    """
    row = parse_json_fields(row, ["review_output", "metadata", "evidence_summary", "run_trace"])
    review_output = row.get("review_output") or {}
    if isinstance(review_output, dict):
        for k, v in review_output.items():
            if k not in row or row[k] is None:
                row[k] = v
    return DailyReviewResponse(**{k: row.get(k) for k in row if k in DailyReviewResponse.model_fields})


@router.get("")
def list_reviews(
    limit: int = Query(default=50, ge=1, le=200),
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    """List daily position reviews."""
    rows = db.execute(
        "SELECT * FROM daily_position_reviews ORDER BY report_date DESC LIMIT ?",
        (limit,),
    )
    items = [_row_to_response(row) for row in rows]
    return {"items": items}


@router.post("/generate", response_model=DailyReviewResponse)
async def generate_daily_review(
    request: DailyReviewRequest,
    llm_service: LLMService = Depends(get_llm_service),
    task_service: AgentTaskService = Depends(get_agent_task_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    _user: str | None = Depends(get_current_user),
    _rate: None = Depends(check_llm_rate_limit),
) -> DailyReviewResponse:
    """Trigger a daily position review and return the result."""
    db = task_service.db
    task = task_service.create_task(AGENT_NAME)
    task_service.update_task_status(task["id"], "running")

    try:
        from app.agents.daily_review.agent import generate_daily_review as run_review

        result = await run_review(db, llm_service, request.report_date, prompt_service=prompt_service)
    except Exception as exc:
        logger.exception("Daily review generation failed: %s", exc)
        task_service.update_task_status(task["id"], "failed", error=str(exc)[:2000])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Daily review generation failed: {str(exc)[:300]}",
        ) from exc

    if result is None:
        task_service.update_task_status(task["id"], "failed", error="No data available for the requested date")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No data available for the requested date",
        )

    trace = result.get("run_trace", []) if isinstance(result, dict) else []
    if isinstance(trace, str):
        try:
            import json as _json
            trace = _json.loads(trace)
        except (ValueError, TypeError):
            trace = []
    progress = extract_trace_metrics(trace) if trace else {"step": "completed"}
    task_service.update_task_status(task["id"], "completed", progress=progress, result={"report_date": request.report_date})

    if isinstance(result, dict):
        # Wrap the result for the response schema
        wrapped = {
            "id": result.get("id", ""),
            "report_date": result.get("report_date", request.report_date),
            "review_output": {k: v for k, v in result.items() if k not in ("id", "report_date", "evidence_pack", "deterministic_context", "raw_llm_response", "fallback_used", "prompt_metadata", "metadata", "run_trace")},
            "metadata": result.get("prompt_metadata") or result.get("metadata"),
            "evidence_summary": result.get("evidence_pack"),
            "run_trace": result.get("run_trace", []),
            "created_at": None,
        }
        return _row_to_response(wrapped)
    return DailyReviewResponse(
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
