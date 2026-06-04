"""Trade decision agent endpoints.

Provides routes for triggering trade decision analyses, listing recent
decisions, fetching decisions by ID, and health checks.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_agent_task_service, get_current_user, get_db, get_llm_service
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.core.rate_limit import check_llm_rate_limit
from app.schemas.trade_decision import (
    TradeDecisionHealthResponse,
    TradeDecisionListResponse,
    TradeDecisionRequest,
    TradeDecisionResponse,
)
from app.services.agent_services import AgentTaskService
from app.services.llm_service import LLMService

router = APIRouter(prefix="/trade-decision", tags=["trade-decision-agent"])
AGENT_NAME = "trade_decision"
logger = logging.getLogger(__name__)


def _row_to_response(row: dict) -> TradeDecisionResponse:
    """Convert a database row to a TradeDecisionResponse."""
    decision_output = row.get("decision_output")
    if isinstance(decision_output, str):
        try:
            decision_output = json.loads(decision_output)
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

    return TradeDecisionResponse(
        id=row["id"],
        decision_type=row["decision_type"],
        symbol=row["symbol"],
        decision_output=decision_output,
        metadata=metadata,
        evidence_summary=evidence_summary,
        run_trace=run_trace,
        created_at=row.get("created_at"),
    )


@router.post("/analyze", response_model=TradeDecisionResponse)
def analyze_trade_decision(
    request: TradeDecisionRequest,
    llm_service: LLMService = Depends(get_llm_service),
    task_service: AgentTaskService = Depends(get_agent_task_service),
    _user: str | None = Depends(get_current_user),
    _rate: None = Depends(check_llm_rate_limit),
) -> TradeDecisionResponse:
    """Trigger a trade decision analysis synchronously and return the result."""
    db = task_service.db

    try:
        from app.agents.trade_decision.agent import analyze_trade
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                analyze_trade(
                    db, llm_service, request.symbol,
                    decision_type=request.decision_type,
                    question=request.question,
                )
            )
        finally:
            loop.close()
    except Exception as exc:
        logger.exception("Trade decision analysis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trade decision analysis failed: {str(exc)[:300]}",
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No data available for the requested analysis",
        )

    return _row_to_response(result) if isinstance(result, dict) else TradeDecisionResponse(
        id="",
        decision_type=request.decision_type,
        symbol=request.symbol,
        decision_output=str(result),
    )


@router.get("/decisions", response_model=TradeDecisionListResponse)
def list_decisions(
    limit: int = Query(default=20, ge=1, le=100),
    symbol: str | None = Query(default=None),
    decision_type: str | None = Query(default=None),
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> TradeDecisionListResponse:
    """List recent trade decisions with optional filters."""
    conditions = []
    params: list = []

    if symbol:
        conditions.append("symbol = ?")
        params.append(symbol)
    if decision_type:
        conditions.append("decision_type = ?")
        params.append(decision_type)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM trade_decisions {where} ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = db.execute(sql, tuple(params))
    items = [_row_to_response(row) for row in rows]
    return TradeDecisionListResponse(items=items)


@router.get("/decisions/{decision_id}", response_model=TradeDecisionResponse)
def get_decision_by_id(
    decision_id: str,
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> TradeDecisionResponse:
    """Get a specific trade decision by ID."""
    row = db.execute_one(
        "SELECT * FROM trade_decisions WHERE id = ?",
        (decision_id,),
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trade decision not found: {decision_id}",
        )
    return _row_to_response(row)


@router.get("/health", response_model=TradeDecisionHealthResponse)
def health_check(
    settings: Settings = Depends(get_settings),
    _user: str | None = Depends(get_current_user),
) -> TradeDecisionHealthResponse:
    """Check trade decision agent health."""
    return TradeDecisionHealthResponse(
        status="ok",
        agent_name=AGENT_NAME,
        llm_configured=bool(settings.llm_api_key),
        message="Trade decision agent is available",
    )
