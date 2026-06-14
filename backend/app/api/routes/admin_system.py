"""Admin system status endpoints."""

from __future__ import annotations

import logging
import platform
import sys
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)

from app.api.deps import get_current_user, get_db
from app.core.database import Database
from app.services.settings_service import get_setting

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/system/status")
def system_status(
    db: Database = Depends(get_db),
    _user: str | None = Depends(get_current_user),
) -> dict:
    """Return system health and configuration status."""
    # Check DB connectivity
    try:
        db.execute("SELECT 1")
        db_healthy = True
    except Exception:
        logger.warning("DB health check failed", exc_info=True)
        db_healthy = False

    # Count records in key tables
    counts = {}
    for table in ["account_snapshots", "position_snapshots", "trade_records", "agent_tasks"]:
        try:
            row = db.execute_one(f"SELECT COUNT(*) as cnt FROM {table}")
            counts[table] = row["cnt"] if row else 0
        except Exception:
            logger.warning("Failed to count rows in %s", table, exc_info=True)
            counts[table] = -1

    # IBKR status
    flex_token = get_setting("FLEX_TOKEN")
    latest_snapshot = db.execute_one("SELECT report_date FROM account_snapshots ORDER BY report_date DESC LIMIT 1")

    # Email status
    email_host = get_setting("email_smtp_host")
    email_password = get_setting("email_smtp_password")
    email_enabled = get_setting("email_enabled")

    # Auth status
    auth_password = get_setting("AUTH_PASSWORD")

    # Scheduler status
    scheduler_enabled = get_setting("SCHEDULER_ENABLED")

    return {
        "status": "ok" if db_healthy else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": {
            "healthy": db_healthy,
            "path": get_setting("SQLITE_PATH") or "data/ibkr_dash.db",
            "record_counts": counts,
        },
        "llm": {
            "configured": bool(get_setting("LLM_API_KEY")),
            "model": get_setting("LLM_DEFAULT_MODEL") or "gpt-4o",
            "base_url": get_setting("LLM_BASE_URL") or "",
        },
        "longbridge": {
            "configured": bool(get_setting("LONGBRIDGE_APP_KEY")),
        },
        "ibkr": {
            "configured": bool(flex_token),
            "has_data": bool(latest_snapshot),
            "latest_date": latest_snapshot["report_date"] if latest_snapshot else None,
        },
        "email": {
            "configured": bool(email_host and email_password),
            "enabled": str(email_enabled).lower() == "true",
        },
        "auth": {
            "password_set": bool(auth_password),
        },
        "scheduler": {
            "enabled": str(scheduler_enabled).lower() != "false",
        },
        "runtime": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "app_env": get_setting("DEBUG") or "development",
        },
    }
