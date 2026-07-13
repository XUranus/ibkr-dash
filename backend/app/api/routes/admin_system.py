"""Admin system status endpoints."""

from __future__ import annotations

import logging
import os
import platform
import sys
import threading
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)

from app.api.deps import get_current_user, get_db
from app.core.database import Database
from app.services.settings_service import get_setting

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Background Longbridge connectivity monitor
# ---------------------------------------------------------------------------

class _LongbridgeMonitor:
    """Periodically checks Longbridge connectivity in a background thread."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._connectivity: str = "unchecked"
        self._last_check: float = 0.0
        self._running = False
        self._thread: threading.Thread | None = None

    @property
    def connectivity(self) -> str:
        with self._lock:
            return self._connectivity

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="lb-monitor")
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def trigger_now(self) -> None:
        """Force an immediate check (e.g. after test-connection)."""
        threading.Thread(target=self._check_once, daemon=True, name="lb-monitor-trigger").start()

    def set_result(self, result: str) -> None:
        """Manually set connectivity (used by test-connection endpoint)."""
        with self._lock:
            self._connectivity = result
            self._last_check = time.time()

    # -- internals --

    def _loop(self) -> None:
        while self._running:
            try:
                self._check_once()
            except Exception:
                logger.debug("Longbridge monitor tick failed", exc_info=True)
            # Sleep in small increments so stop() is responsive
            for _ in range(60):
                if not self._running:
                    return
                time.sleep(1)

    def _check_once(self) -> None:
        app_key = get_setting("LONGBRIDGE_APP_KEY")
        app_secret = get_setting("LONGBRIDGE_APP_SECRET")
        access_token = get_setting("LONGBRIDGE_ACCESS_TOKEN")

        if not app_key or not access_token:
            self._set("unchecked")
            return

        try:
            sdk_ok = False
            try:
                import longport  # noqa: F401
                sdk_ok = True
            except ImportError:
                pass

            if not sdk_ok:
                self._set("unchecked")
                return

            os.environ["LONGPORT_APP_KEY"] = str(app_key)
            os.environ["LONGPORT_APP_SECRET"] = str(app_secret or "")
            os.environ["LONGPORT_ACCESS_TOKEN"] = str(access_token)

            # Suppress SDK verbose logging
            import logging
            logging.getLogger("longport").setLevel(logging.WARNING)

            from longport.openapi import QuoteContext, Config
            config = Config.from_apikey_env()
            ctx = QuoteContext(config)
            resp = ctx.quote(["AAPL.US"])
            self._set("ok" if resp else "degraded")
        except Exception as exc:
            self._set("error")
            logger.debug("Longbridge connectivity check failed: %s", exc)

    def _set(self, value: str) -> None:
        with self._lock:
            self._connectivity = value
            self._last_check = time.time()


_lb_monitor = _LongbridgeMonitor()


def _build_longbridge_status() -> dict:
    """Build Longbridge config and connectivity status (non-blocking)."""
    app_key = get_setting("LONGBRIDGE_APP_KEY")
    app_secret = get_setting("LONGBRIDGE_APP_SECRET")
    access_token = get_setting("LONGBRIDGE_ACCESS_TOKEN")

    sdk_installed = False
    sdk_version = None
    try:
        import longport
        sdk_installed = True
        sdk_version = getattr(longport, "__version__", None) or getattr(longport, "version", None)
    except ImportError:
        pass

    configured = bool(app_key and access_token)
    connectivity = _lb_monitor.connectivity if configured else "unchecked"

    return {
        "configured": configured,
        "app_key_configured": bool(app_key),
        "app_secret_configured": bool(app_secret),
        "access_token_configured": bool(access_token),
        "sdk_installed": sdk_installed,
        "sdk_version": sdk_version,
        "connectivity": connectivity,
    }


@router.post("/longbridge/test-connection")
def test_longbridge_connection(
    _user: str | None = Depends(get_current_user),
) -> dict:
    """Test Longbridge API connectivity and return detailed results."""
    app_key = get_setting("LONGBRIDGE_APP_KEY")
    app_secret = get_setting("LONGBRIDGE_APP_SECRET")
    access_token = get_setting("LONGBRIDGE_ACCESS_TOKEN")

    if not app_key or not access_token:
        return {
            "success": False,
            "message": "Longbridge credentials not configured (app_key or access_token missing).",
            "error_code": "NOT_CONFIGURED",
            "quote_sample": None,
            "data_limitations": [],
        }

    # Check SDK
    try:
        import longport  # noqa: F401
    except ImportError:
        return {
            "success": False,
            "message": "longport SDK not installed. Run: pip install longport",
            "error_code": "SDK_NOT_INSTALLED",
            "quote_sample": None,
            "data_limitations": [],
        }

    # Test connection
    import os
    os.environ["LONGPORT_APP_KEY"] = str(app_key)
    os.environ["LONGPORT_APP_SECRET"] = str(app_secret or "")
    os.environ["LONGPORT_ACCESS_TOKEN"] = str(access_token)

    try:
        from longport.openapi import QuoteContext, Config
        config = Config.from_apikey_env()
        ctx = QuoteContext(config)
        resp = ctx.quote(["AAPL.US"])
        if not resp:
            return {
                "success": False,
                "message": "API connected but returned no data.",
                "error_code": "NO_DATA",
                "quote_sample": None,
                "data_limitations": [],
            }
        q = resp[0]
        # Update monitor with successful result
        _lb_monitor.set_result("ok")
        return {
            "success": True,
            "message": "Connection successful.",
            "error_code": None,
            "quote_sample": {
                "symbol": str(q.symbol),
                "last_done": str(q.last_done),
                "prev_close": str(q.prev_close),
                "volume": int(q.volume),
                "turnover": str(q.turnover),
            },
            "data_limitations": [],
        }
    except Exception as exc:
        _lb_monitor.set_result("error")
        return {
            "success": False,
            "message": f"Connection failed: {str(exc)[:200]}",
            "error_code": "CONNECTION_FAILED",
            "quote_sample": None,
            "data_limitations": [],
        }


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
        "longbridge": _build_longbridge_status(),
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
