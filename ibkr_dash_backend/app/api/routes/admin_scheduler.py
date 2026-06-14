"""Admin scheduler endpoints.

Provides manual trigger for the import pipeline, AI report generation,
and import history.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user, get_db, get_llm_service
from app.core.database import Database
from app.services.import_service import get_import_history, run_import
from app.services.llm_service import LLMService

router = APIRouter(prefix="/admin/scheduler", tags=["admin-scheduler"])
logger = logging.getLogger(__name__)


@router.post("/trigger-import")
def trigger_import(
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    """Manually trigger the import pipeline (fetch + import).

    Returns the import results and any errors.
    """
    result = run_import(db)
    return {
        "success": len(result["errors"]) == 0,
        "files": result["files"],
        "errors": result["errors"],
        "started_at": result["started_at"],
        "duration_ms": result["duration_ms"],
    }


@router.get("/import-history")
def list_import_history(
    limit: int = Query(default=100, ge=1, le=500),
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    """List recent import history records."""
    items = get_import_history(db, limit=limit)
    return {"items": items}


@router.post("/trigger-ai-report")
async def trigger_ai_report(
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service),
) -> dict:
    """Manually trigger AI position analysis report generation."""
    from app.agents.position_analysis.agent import generate_position_analysis

    account = db.execute_one(
        "SELECT report_date FROM account_snapshots ORDER BY report_date DESC LIMIT 1"
    )
    if not account:
        raise HTTPException(
            status_code=422,
            detail="No account data available. Import data first.",
        )

    report_date = account["report_date"]
    t0 = time.monotonic()
    try:
        result = await generate_position_analysis(db, llm_service, report_date)
    except Exception as exc:
        logger.exception("AI report generation failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"AI report failed: {str(exc)[:300]}",
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=503,
            detail="LLM not configured or analysis returned no results",
        )

    duration_ms = int((time.monotonic() - t0) * 1000)
    return {
        "success": True,
        "report_date": report_date,
        "created_at": result.get("created_at", ""),
        "duration_ms": duration_ms,
    }
