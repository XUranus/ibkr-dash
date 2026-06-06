"""Admin system status endpoints."""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_db, get_app_settings
from app.core.config import Settings
from app.core.database import Database

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/system/status")
def system_status(
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _user: str | None = Depends(get_current_user),
) -> dict:
    """Return system health and configuration status."""
    # Check DB connectivity
    try:
        db.execute("SELECT 1")
        db_healthy = True
    except Exception:
        db_healthy = False

    # Count records in key tables
    counts = {}
    for table in ["account_snapshots", "position_snapshots", "trade_records", "agent_tasks"]:
        try:
            row = db.execute_one(f"SELECT COUNT(*) as cnt FROM {table}")
            counts[table] = row["cnt"] if row else 0
        except Exception:
            counts[table] = -1

    return {
        "status": "ok" if db_healthy else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": {
            "healthy": db_healthy,
            "path": settings.sqlite_path,
            "record_counts": counts,
        },
        "llm": {
            "configured": bool(settings.llm_api_key),
            "model": settings.llm_default_model,
            "base_url": settings.llm_base_url,
        },
        "longbridge": {
            "configured": bool(settings.longbridge_app_key),
        },
        "runtime": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "app_env": settings.app_env,
        },
    }
