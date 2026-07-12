"""Admin market events management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user, get_db
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.services.market_event_service import (
    get_upcoming_events,
    seed_market_events,
    sync_market_events,
    generate_market_event_analysis,
    get_latest_analysis,
)

router = APIRouter(prefix="/admin/market-events", tags=["admin-market-events"])


@router.get("")
def list_all_events(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    """List all market events with pagination."""
    rows = db.execute(
        "SELECT * FROM market_events ORDER BY scheduled_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    )
    total_row = db.execute_one("SELECT COUNT(*) as cnt FROM market_events")
    return {
        "items": rows,
        "total": total_row["cnt"] if total_row else 0,
        "limit": limit,
        "offset": offset,
    }


@router.post("/seed")
def admin_seed_events(
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    """Seed market events (admin)."""
    count = seed_market_events(db)
    return {"seeded": count}


@router.post("/sync")
def admin_sync_events(
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Sync market events from external sources (admin)."""
    bls_key = getattr(settings, "bls_api_key", None)
    results = sync_market_events(db, bls_api_key=bls_key)
    return {"synced": results}


@router.delete("/{event_id}")
def delete_event(
    event_id: str,
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    """Delete a market event."""
    existing = db.execute_one("SELECT id FROM market_events WHERE id = ?", (event_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Event not found")
    db.execute("DELETE FROM market_events WHERE id = ?", (event_id,))
    return {"deleted": event_id}


@router.post("/analysis/generate")
def admin_generate_analysis(
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Generate AI market event analysis (admin)."""
    from app.services.llm_service import LLMService
    llm_service = LLMService(settings)
    result = generate_market_event_analysis(db, llm_service)
    if result is None:
        return {"analysis": None, "message": "LLM not available or no events found"}
    return {"analysis": result}


@router.get("/analysis")
def admin_get_analysis(
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    """Get the latest AI market event analysis (admin)."""
    analysis = get_latest_analysis(db)
    return {"analysis": analysis}
