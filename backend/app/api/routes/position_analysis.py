"""Position analysis endpoints.

Provides routes for fetching the latest position analysis and
manually triggering a new analysis.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user, get_db, get_llm_service
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.services.llm_service import LLMService

router = APIRouter(prefix="/position-analysis", tags=["position-analysis"])
logger = logging.getLogger(__name__)


@router.get("/latest")
def get_latest_analysis(
    lang: str = Query(default="zh", pattern="^(zh|en)$"),
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    """Get the latest position analysis report.

    Returns the most recent analysis in the requested language.
    Returns 404 if no analysis exists.
    """
    row = db.execute_one(
        "SELECT * FROM position_analysis ORDER BY created_at DESC LIMIT 1"
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No position analysis available",
        )

    report = row.get("analysis_zh") if lang == "zh" else row.get("analysis_en")
    if not report:
        report = row.get("analysis_zh") or row.get("analysis_en") or ""

    return {
        "id": row.get("id"),
        "report_date": row.get("report_date"),
        "lang": lang,
        "report": report,
        "created_at": row.get("created_at"),
    }


@router.post("/generate")
async def trigger_analysis(
    llm_service: LLMService = Depends(get_llm_service),
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    """Manually trigger a position analysis generation."""
    from app.agents.position_analysis.agent import generate_position_analysis

    account = db.execute_one(
        "SELECT report_date FROM account_snapshots ORDER BY report_date DESC LIMIT 1"
    )
    if not account:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No account data available",
        )

    report_date = account["report_date"]
    try:
        result = await generate_position_analysis(db, llm_service, report_date)
    except Exception as exc:
        logger.exception("Position analysis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(exc)[:300]}",
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM not configured or analysis returned no results",
        )

    return result
