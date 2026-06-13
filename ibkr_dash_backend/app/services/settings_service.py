"""Unified settings service.

Reads configuration from admin_settings table first, falls back to env vars.
Both backend and worker use this service for configuration.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from app.core.database import Database

logger = logging.getLogger(__name__)

# All configuration keys with their categories and defaults
SETTINGS_SCHEMA: dict[str, dict[str, Any]] = {
    # IBKR Connection
    "FLEX_TOKEN": {"category": "ibkr", "label": "Flex Token", "type": "password", "default": ""},
    "FLEX_QUERY_IDS": {"category": "ibkr", "label": "Flex Query IDs", "type": "text", "default": "1532356,1532359"},
    "FLEX_BASE_URL": {"category": "ibkr", "label": "Flex Base URL", "type": "text", "default": "https://www.interactivebrokers.com/AccountManagement/FlexWebService"},
    "FLEX_POLL_INTERVAL_SECONDS": {"category": "ibkr", "label": "Poll Interval (s)", "type": "number", "default": "10"},
    "FLEX_MAX_POLL_RETRIES": {"category": "ibkr", "label": "Max Poll Retries", "type": "number", "default": "60"},

    # AI / LLM
    "LLM_API_KEY": {"category": "llm", "label": "API Key", "type": "password", "default": ""},
    "LLM_BASE_URL": {"category": "llm", "label": "Base URL", "type": "text", "default": "https://api.openai.com/v1"},
    "LLM_DEFAULT_MODEL": {"category": "llm", "label": "Default Model", "type": "text", "default": "gpt-4o"},
    "LLM_TEMPERATURE": {"category": "llm", "label": "Temperature", "type": "number", "default": "0.1"},
    "LLM_MAX_TOKENS": {"category": "llm", "label": "Max Tokens", "type": "number", "default": "8192"},
    "BLS_API_KEY": {"category": "llm", "label": "BLS API Key", "type": "password", "default": ""},

    # Scheduler
    "SCHEDULER_ENABLED": {"category": "scheduler", "label": "Enabled", "type": "boolean", "default": "true"},
    "SCHEDULER_HOUR": {"category": "scheduler", "label": "Hour", "type": "number", "default": "12"},
    "SCHEDULER_MINUTE": {"category": "scheduler", "label": "Minute", "type": "number", "default": "30"},
    "SCHEDULER_TIMEZONE": {"category": "scheduler", "label": "Timezone", "type": "text", "default": "Asia/Shanghai"},

    # Auth
    "AUTH_USERNAME": {"category": "auth", "label": "Username", "type": "text", "default": "admin"},
    "AUTH_PASSWORD": {"category": "auth", "label": "Password", "type": "password", "default": ""},

    # Advanced
    "SQLITE_PATH": {"category": "advanced", "label": "SQLite Path", "type": "text", "default": "data/ibkr_dash.db"},
    "DEBUG": {"category": "advanced", "label": "Debug Mode", "type": "boolean", "default": "false"},
    "LOG_LEVEL": {"category": "advanced", "label": "Log Level", "type": "text", "default": "INFO"},
    "CORS_ORIGINS": {"category": "advanced", "label": "CORS Origins", "type": "text", "default": "http://localhost:5173"},
    "DATA_DIR": {"category": "advanced", "label": "Data Directory", "type": "text", "default": "data/flex_exports"},
}


def get_setting(db: Database, key: str) -> str | None:
    """Get a setting value from admin_settings table, falling back to env."""
    row = db.execute_one("SELECT value FROM admin_settings WHERE key = ?", (key,))
    if row and row.get("value") is not None:
        return str(row["value"])
    return os.getenv(key)


def get_setting_with_default(db: Database, key: str) -> str:
    """Get a setting value with default from schema."""
    schema = SETTINGS_SCHEMA.get(key, {})
    default = schema.get("default", "")
    return get_setting(db, key) or str(default)


def set_setting(db: Database, key: str, value: str) -> None:
    """Set a setting value in admin_settings table."""
    db.upsert("admin_settings", {"key": key, "value": value}, conflict_cols=["key"])


def get_all_settings(db: Database) -> dict[str, dict[str, Any]]:
    """Get all settings with their current values, organized by category.

    Returns dict of category -> list of {key, label, value, type, default}.
    """
    # Get all stored settings
    rows = db.execute("SELECT key, value FROM admin_settings")
    stored = {r["key"]: r["value"] for r in rows}

    result: dict[str, list[dict[str, Any]]] = {}
    for key, meta in SETTINGS_SCHEMA.items():
        category = meta["category"]
        if category not in result:
            result[category] = []

        # Priority: admin_settings > env > default
        value = stored.get(key) or os.getenv(key, meta["default"])

        # Mask sensitive values
        display_value = value
        if meta["type"] == "password" and value:
            display_value = value[:4] + "****" + value[-4:] if len(value) > 8 else "****"

        result[category].append({
            "key": key,
            "label": meta["label"],
            "value": value,
            "display_value": display_value,
            "type": meta["type"],
            "default": meta["default"],
            "is_set": key in stored,
        })

    return result


def update_settings(db: Database, settings: dict[str, str]) -> int:
    """Update multiple settings in admin_settings table.

    Returns the number of settings updated.
    """
    count = 0
    for key, value in settings.items():
        if key in SETTINGS_SCHEMA:
            set_setting(db, key, value)
            count += 1
    return count


def reset_settings(db: Database, keys: list[str] | None = None) -> int:
    """Reset settings to defaults (remove from admin_settings).

    If keys is None, reset all settings.
    Returns the number of settings reset.
    """
    if keys is None:
        db.execute("DELETE FROM admin_settings")
        return len(SETTINGS_SCHEMA)

    count = 0
    for key in keys:
        if key in SETTINGS_SCHEMA:
            db.execute("DELETE FROM admin_settings WHERE key = ?", (key,))
            count += 1
    return count
