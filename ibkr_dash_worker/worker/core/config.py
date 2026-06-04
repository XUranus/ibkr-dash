"""Worker application configuration.

All settings are loaded from environment variables with sensible defaults.
No external dependencies -- SQLite is the sole data store.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass  # python-dotenv is optional; env vars can be set externally


def _read_bool(name: str, default: bool) -> bool:
    """Read a boolean environment variable."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _read_int(name: str, default: int) -> int:
    """Read an integer environment variable."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value.strip())
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Worker settings loaded from environment variables."""

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
    flex_query_id_daily: str
    flex_poll_interval_seconds: int
    flex_max_poll_retries: int

    # --- Backend integration ---
    backend_base_url: str
    daily_review_internal_token: str


@lru_cache
def get_settings() -> Settings:
    """Return cached singleton settings instance."""
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        debug=_read_bool("DEBUG", False),
        sqlite_path=os.getenv(
            "SQLITE_PATH",
            str(BASE_DIR.parent / "data" / "ibkr_dash.db"),
        ),
        data_dir=os.getenv(
            "DATA_DIR",
            str(BASE_DIR.parent / "data" / "flex_exports"),
        ),
        scheduler_enabled=_read_bool("SCHEDULER_ENABLED", True),
        scheduler_hour=_read_int("SCHEDULER_HOUR", 12),
        scheduler_minute=_read_int("SCHEDULER_MINUTE", 30),
        scheduler_timezone=os.getenv("SCHEDULER_TIMEZONE", "Asia/Shanghai"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        flex_base_url=os.getenv(
            "FLEX_BASE_URL",
            "https://www.interactivebrokers.com/AccountManagement/FlexWebService",
        ),
        flex_token=os.getenv("FLEX_TOKEN", ""),
        flex_query_id_daily=os.getenv("FLEX_QUERY_ID_DAILY", ""),
        flex_poll_interval_seconds=_read_int("FLEX_POLL_INTERVAL_SECONDS", 10),
        flex_max_poll_retries=_read_int("FLEX_MAX_POLL_RETRIES", 60),
        backend_base_url=os.getenv("BACKEND_BASE_URL", "http://localhost:8000"),
        daily_review_internal_token=os.getenv("DAILY_REVIEW_INTERNAL_TOKEN", ""),
    )
