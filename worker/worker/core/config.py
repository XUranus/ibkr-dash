"""Worker application configuration.

Reads from the shared JSON config file (data/config.json).
No environment variables. No .env file.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

# Project root: worker/core/config.py -> worker/core -> worker -> worker -> project root
_BASE_DIR = Path(__file__).resolve().parents[2]  # worker/
_PROJECT_ROOT = _BASE_DIR.parent  # ibkr-dash/
_CONFIG_PATH = Path(os.environ.get("CONFIG_PATH", str(_PROJECT_ROOT / "data" / "config.json")))


def _load_json_config() -> dict:
    """Load config from the shared JSON file."""
    if _CONFIG_PATH.exists():
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


@dataclass(frozen=True)
class Settings:
    """Worker settings loaded from the shared JSON config."""

    # --- App ---
    app_env: str
    debug: bool

    # --- SQLite (shared with backend) ---
    sqlite_path: str

    # --- Data directory where Flex CSV files live ---
    data_dir: str

    # --- Scheduler ---
    scheduler_enabled: bool
    scheduler_hour: int
    scheduler_minute: int
    scheduler_timezone: str

    # --- Logging ---
    log_level: str

    # --- IBKR Flex Web Service ---
    flex_base_url: str
    flex_token: str
    flex_query_ids: str  # comma-separated, e.g. "1532356,1532359"
    flex_poll_interval_seconds: int
    flex_max_poll_retries: int

    # --- Backend integration ---
    backend_base_url: str
    daily_review_internal_token: str

    # --- Market Events ---
    market_events_sync_interval_hours: int

    # --- LLM (for BLS API key) ---
    bls_api_key: str


def get_settings() -> Settings:
    """Build Settings from the shared JSON config.

    Not cached — reads fresh each time so admin UI changes take effect.
    """
    cfg = _load_json_config()

    ibkr = cfg.get("ibkr", {})
    scheduler = cfg.get("scheduler", {})
    advanced = cfg.get("advanced", {})
    worker = cfg.get("worker", {})

    return Settings(
        app_env=str(advanced.get("app_env", "development")),
        debug=bool(advanced.get("debug", False)),
        sqlite_path=str(advanced.get("sqlite_path", str(_PROJECT_ROOT / "data" / "ibkr_dash.db"))),
        data_dir=str(advanced.get("data_dir", str(_PROJECT_ROOT / "data" / "flex_exports"))),
        scheduler_enabled=bool(scheduler.get("enabled", True)),
        scheduler_hour=int(scheduler.get("hour", 12)),
        scheduler_minute=int(scheduler.get("minute", 30)),
        scheduler_timezone=str(scheduler.get("timezone", "Asia/Shanghai")),
        log_level=str(advanced.get("log_level", "INFO")),
        flex_base_url=str(ibkr.get("flex_base_url", "https://www.interactivebrokers.com/AccountManagement/FlexWebService")),
        flex_token=str(ibkr.get("flex_token", "")),
        flex_query_ids=str(ibkr.get("flex_query_ids", "1532356,1532359")),
        flex_poll_interval_seconds=int(ibkr.get("flex_poll_interval_seconds", 10)),
        flex_max_poll_retries=int(ibkr.get("flex_max_poll_retries", 60)),
        backend_base_url=str(worker.get("backend_base_url", "http://localhost:8000")),
        daily_review_internal_token=str(worker.get("daily_review_internal_token", "")),
        market_events_sync_interval_hours=int(scheduler.get("market_events_sync_interval_hours", 24)),
        bls_api_key=str(cfg.get("llm", {}).get("bls_api_key", "")),
    )
