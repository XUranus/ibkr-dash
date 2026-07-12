"""Admin LLM call metrics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_llm_call_metrics_service
from app.services.llm_call_metrics_service import LLMCallMetricsService

router = APIRouter(prefix="/admin/llm-calls", tags=["admin-llm-calls"])


@router.get("")
def list_llm_calls(
    agent_name: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user: str | None = Depends(get_current_user),
    svc: LLMCallMetricsService = Depends(get_llm_call_metrics_service),
) -> dict:
    """List LLM call metrics with optional agent filter."""
    return svc.list_calls(agent_name=agent_name, limit=limit, offset=offset)


@router.get("/stats")
def get_llm_call_stats(
    days: int = Query(default=30, ge=1, le=365),
    _user: str | None = Depends(get_current_user),
    svc: LLMCallMetricsService = Depends(get_llm_call_metrics_service),
) -> dict:
    """Get aggregated LLM call statistics."""
    return svc.get_stats(days=days)


@router.get("/breakdown")
def get_agent_breakdown(
    days: int = Query(default=30, ge=1, le=365),
    _user: str | None = Depends(get_current_user),
    svc: LLMCallMetricsService = Depends(get_llm_call_metrics_service),
) -> dict:
    """Get per-agent LLM call breakdown."""
    items = svc.get_agent_breakdown(days=days)
    return {"items": items}
