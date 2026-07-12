"""Market events endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_db, get_llm_service, get_optional_user
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.services.llm_service import LLMService
from app.services.market_event_service import (
    generate_market_event_analysis,
    get_latest_analysis,
    get_today_events,
    get_upcoming_events,
    seed_market_events,
    sync_market_events,
)

router = APIRouter(prefix="/market-events", tags=["market-events"])


@router.get("/upcoming")
def list_upcoming_events(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=20, ge=1, le=100),
    _user: str | None = Depends(get_optional_user),
    db: Database = Depends(get_db),
) -> dict:
    """Get upcoming market events."""
    events = get_upcoming_events(db, days=days, limit=limit)
    return {"items": events, "total": len(events)}


@router.get("/today")
def list_today_events(
    _user: str | None = Depends(get_optional_user),
    db: Database = Depends(get_db),
) -> dict:
    """Get today's market events."""
    events = get_today_events(db)
    return {"items": events, "total": len(events)}


@router.post("/seed")
def seed_events(
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    """Seed market events: holidays + FOMC from Fed website."""
    count = seed_market_events(db)
    return {"seeded": count}


@router.post("/sync")
def sync_events(
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    llm_service: LLMService = Depends(get_llm_service),
) -> dict:
    """Sync market events from external sources (Fed FOMC, BLS API).

    If LLM is available, also generates an AI risk analysis.
    """
    bls_key = getattr(settings, 'bls_api_key', None)
    results = sync_market_events(db, bls_api_key=bls_key)

    # Try to generate AI analysis (non-blocking, best-effort)
    analysis = None
    try:
        analysis = generate_market_event_analysis(db, llm_service)
    except Exception:
        pass  # analysis is optional — sync always succeeds
    results["analysis_generated"] = analysis is not None

    return {"synced": results}


@router.get("/analysis")
def get_analysis(
    _user: str | None = Depends(get_optional_user),
    db: Database = Depends(get_db),
) -> dict:
    """Get the latest AI-generated market risk analysis."""
    analysis = get_latest_analysis(db)
    return {"analysis": analysis}


@router.post("/analysis/generate")
def generate_analysis(
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service),
) -> dict:
    """Generate a new AI market risk analysis."""
    analysis = generate_market_event_analysis(db, llm_service)
    if analysis is None:
        return {"analysis": None, "message": "LLM not available or no events found"}
    return {"analysis": analysis}
