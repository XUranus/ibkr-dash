"""Risk assessment agent endpoints.

Provides routes for triggering risk assessments, listing recent assessments,
fetching assessments by ID, and health checks.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_agent_task_service, get_current_user, get_db, get_llm_service
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.core.rate_limit import check_llm_rate_limit
from app.schemas.risk_assessment import (
    RiskAssessmentHealthResponse,
    RiskAssessmentListResponse,
    RiskAssessmentRequest,
    RiskAssessmentResponse,
)
from app.services.agent_services import AgentTaskService
from app.services.llm_service import LLMService

router = APIRouter(prefix="/risk-assessment", tags=["risk-assessment-agent"])
AGENT_NAME = "risk_assessment"
logger = logging.getLogger(__name__)


def _row_to_response(row: dict) -> RiskAssessmentResponse:
    """Convert a database row to a RiskAssessmentResponse."""
    risk_report = row.get("risk_report")
    if isinstance(risk_report, str):
        try:
            risk_report = json.loads(risk_report)
        except (json.JSONDecodeError, TypeError):
            pass

    metadata = row.get("metadata")
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except (json.JSONDecodeError, TypeError):
            pass

    run_trace = row.get("run_trace")
    if isinstance(run_trace, str):
        try:
            run_trace = json.loads(run_trace)
        except (json.JSONDecodeError, TypeError):
            pass

    return RiskAssessmentResponse(
        id=row["id"],
        assessment_type=row["assessment_type"],
        risk_report=risk_report,
        metadata=metadata,
        run_trace=run_trace,
        created_at=row.get("created_at"),
    )


@router.post("/assess", response_model=RiskAssessmentResponse)
def trigger_risk_assessment(
    request: RiskAssessmentRequest,
    llm_service: LLMService = Depends(get_llm_service),
    task_service: AgentTaskService = Depends(get_agent_task_service),
    _user: str | None = Depends(get_current_user),
    _rate: None = Depends(check_llm_rate_limit),
) -> RiskAssessmentResponse:
    """Trigger a risk assessment synchronously and return the result."""
    db = task_service.db

    try:
        from app.agents.risk_assessment.agent import assess_risk
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                assess_risk(db, llm_service, question=request.question)
            )
        finally:
            loop.close()
    except Exception as exc:
        logger.exception("Risk assessment failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk assessment failed: {str(exc)[:300]}",
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No data available for the risk assessment",
        )

    return _row_to_response(result) if isinstance(result, dict) else RiskAssessmentResponse(
        id="",
        assessment_type="portfolio_risk",
        risk_report=str(result),
    )


@router.get("/assessments", response_model=RiskAssessmentListResponse)
def list_assessments(
    limit: int = Query(default=20, ge=1, le=100),
    assessment_type: str | None = Query(default=None),
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> RiskAssessmentListResponse:
    """List recent risk assessments with optional filters."""
    conditions = []
    params: list = []

    if assessment_type:
        conditions.append("assessment_type = ?")
        params.append(assessment_type)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM risk_assessments {where} ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = db.execute(sql, tuple(params))
    items = [_row_to_response(row) for row in rows]
    return RiskAssessmentListResponse(items=items)


@router.get("/assessments/{assessment_id}", response_model=RiskAssessmentResponse)
def get_assessment_by_id(
    assessment_id: str,
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> RiskAssessmentResponse:
    """Get a specific risk assessment by ID."""
    row = db.execute_one(
        "SELECT * FROM risk_assessments WHERE id = ?",
        (assessment_id,),
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk assessment not found: {assessment_id}",
        )
    return _row_to_response(row)


@router.get("/health", response_model=RiskAssessmentHealthResponse)
def health_check(
    settings: Settings = Depends(get_settings),
    _user: str | None = Depends(get_current_user),
) -> RiskAssessmentHealthResponse:
    """Check risk assessment agent health."""
    return RiskAssessmentHealthResponse(
        status="ok",
        agent_name=AGENT_NAME,
        llm_configured=bool(settings.llm_api_key),
        message="Risk assessment agent is available",
    )
