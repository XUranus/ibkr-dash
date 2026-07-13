"""Trade decision agent endpoints.

Provides routes for triggering trade decision analyses, listing recent
decisions, fetching decisions by ID, and health checks.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_agent_task_service, get_current_user, get_db, get_llm_service, get_prompt_service
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.core.rate_limit import check_llm_rate_limit
from app.schemas.trade_decision import (
    TradeDecisionHealthResponse,
    TradeDecisionListResponse,
    TradeDecisionRequest,
    TradeDecisionResponse,
)
from app.services.agent_services import AgentTaskService, extract_trace_metrics
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService
from app.utils.json_fields import parse_json_fields

router = APIRouter(prefix="/trade-decision", tags=["trade-decision-agent"])
AGENT_NAME = "trade_decision"
logger = logging.getLogger(__name__)


def _row_to_response(row: dict) -> TradeDecisionResponse:
    """Convert a database row to a TradeDecisionResponse."""
    import json as _json
    row = parse_json_fields(row, ["decision_output", "metadata", "evidence_summary", "run_trace"])
    # TradeDecisionResponse expects these fields as str, re-serialize if parsed to dict/list
    for field in ("decision_output", "metadata", "evidence_summary", "run_trace"):
        val = row.get(field)
        if isinstance(val, (dict, list)):
            row[field] = _json.dumps(val, ensure_ascii=False)
    return TradeDecisionResponse(**{k: row.get(k) for k in row if k in TradeDecisionResponse.model_fields})


@router.post("/analyze", response_model=TradeDecisionResponse)
async def analyze_trade_decision(
    request: TradeDecisionRequest,
    llm_service: LLMService = Depends(get_llm_service),
    task_service: AgentTaskService = Depends(get_agent_task_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    _user: str | None = Depends(get_current_user),
    _rate: None = Depends(check_llm_rate_limit),
) -> TradeDecisionResponse:
    """Trigger a trade decision analysis and return the result."""
    db = task_service.db
    task = task_service.create_task(AGENT_NAME)
    task_service.update_task_status(task["id"], "running")

    try:
        from app.agents.trade_decision.agent import analyze_trade

        result = await analyze_trade(
            db, llm_service, request.symbol,
            decision_type=request.decision_type,
            question=request.question,
            prompt_service=prompt_service,
        )
    except Exception as exc:
        logger.exception("Trade decision analysis failed: %s", exc)
        task_service.update_task_status(task["id"], "failed", error=str(exc)[:2000])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trade decision analysis failed: {str(exc)[:300]}",
        ) from exc

    if result is None:
        task_service.update_task_status(task["id"], "failed", error="No data available for the requested analysis")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No data available for the requested analysis",
        )

    trace = result.get("run_trace", []) if isinstance(result, dict) else []
    if isinstance(trace, str):
        try:
            import json as _json
            trace = _json.loads(trace)
        except (ValueError, TypeError):
            trace = []
    progress = extract_trace_metrics(trace) if trace else {"step": "completed"}
    task_service.update_task_status(task["id"], "completed", progress=progress, result={"symbol": request.symbol, "decision_type": request.decision_type})

    if isinstance(result, dict):
        # Wrap the result for the response schema
        wrapped = {
            "id": result.get("id", ""),
            "decision_type": result.get("decision_type", request.decision_type),
            "symbol": result.get("symbol", request.symbol),
            "decision_output": {k: v for k, v in result.items() if k not in ("id", "decision_type", "symbol", "evidence_pack", "raw_llm_response", "fallback_used", "prompt_metadata")},
            "metadata": result.get("prompt_metadata"),
            "evidence_summary": result.get("evidence_pack"),
            "run_trace": [],
            "created_at": None,
        }
        return _row_to_response(wrapped)
    return TradeDecisionResponse(
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


@router.get("/decisions/{decision_id}/report")
def get_decision_report(
    decision_id: str,
    lang: str = Query(default="zh", pattern="^(zh|en)$"),
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    """Get the markdown report for a trade decision.

    Returns the bilingual markdown report stored with the decision.
    """
    row = db.execute_one(
        "SELECT * FROM trade_decisions WHERE id = ?",
        (decision_id,),
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trade decision not found: {decision_id}",
        )

    # Parse the decision output to get report
    import json
    from app.utils.json_fields import parse_json_fields
    parsed = parse_json_fields(row, ["decision_output"])
    output = parsed.get("decision_output", {})

    # Try to get pre-generated report
    report_key = f"report_{lang}"
    report = output.get(report_key)

    if not report:
        # Generate on-the-fly
        from app.agents.report_generator import generate_trade_decision_report
        symbol = row.get("symbol", "")
        report = generate_trade_decision_report(output, symbol, lang=lang)

    return {
        "decision_id": decision_id,
        "symbol": row.get("symbol", ""),
        "lang": lang,
        "report": report,
    }


@router.get("/health", response_model=TradeDecisionHealthResponse)
def health_check(
    settings: Settings = Depends(get_settings),
    _user: str | None = Depends(get_current_user),
) -> TradeDecisionHealthResponse:
    """Check trade decision agent health."""
    return TradeDecisionHealthResponse(
        enabled=True,
        llm_configured=bool(settings.llm_api_key),
        longbridge_configured=bool(getattr(settings, "longbridge_app_key", None)),
        trade_review_available=True,
        account_data_source="ibkr",
        public_market_data_source="longbridge",
        message="Trade decision agent is available",
    )
