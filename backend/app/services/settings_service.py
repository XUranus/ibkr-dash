"""Unified settings service.

All configuration reads/writes go through the JSON-backed settings manager.
Provides the admin API with categorized settings and UI metadata.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.settings_manager import get_manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapping: flat KEY (used by admin UI / worker) → JSON dot-path
# ---------------------------------------------------------------------------

_KEY_TO_PATH: dict[str, str] = {
    "FLEX_TOKEN": "ibkr.flex_token",
    "FLEX_QUERY_IDS": "ibkr.flex_query_ids",
    "FLEX_BASE_URL": "ibkr.flex_base_url",
    "FLEX_POLL_INTERVAL_SECONDS": "ibkr.flex_poll_interval_seconds",
    "FLEX_MAX_POLL_RETRIES": "ibkr.flex_max_poll_retries",
    "LLM_API_KEY": "llm.api_key",
    "LLM_BASE_URL": "llm.base_url",
    "LLM_DEFAULT_MODEL": "llm.default_model",
    "LLM_TEMPERATURE": "llm.temperature",
    "LLM_MAX_TOKENS": "llm.max_tokens",
    "BLS_API_KEY": "llm.bls_api_key",
    "SCHEDULER_ENABLED": "scheduler.enabled",
    "SCHEDULER_HOUR": "scheduler.hour",
    "SCHEDULER_MINUTE": "scheduler.minute",
    "SCHEDULER_TIMEZONE": "scheduler.timezone",
    "MARKET_EVENTS_SYNC_INTERVAL_HOURS": "scheduler.market_events_sync_interval_hours",
    "AUTH_USERNAME": "auth.username",
    "AUTH_PASSWORD": "auth.password",
    "COOKIE_SECURE": "auth.cookie_secure",
    "LONGBRIDGE_APP_KEY": "longbridge.app_key",
    "LONGBRIDGE_APP_SECRET": "longbridge.app_secret",
    "LONGBRIDGE_ACCESS_TOKEN": "longbridge.access_token",
    "SQLITE_PATH": "advanced.sqlite_path",
    "DEBUG": "advanced.debug",
    "LOG_LEVEL": "advanced.log_level",
    "CORS_ORIGINS": "advanced.cors_origins",
    "DATA_DIR": "advanced.data_dir",
    "AUDIT_LLM_CALLS": "advanced.audit_llm_calls",
    "APP_NAME": "advanced.app_name",
    "APP_ENV": "advanced.app_env",
    "CACHE_TTL_SECONDS": "advanced.cache_ttl_seconds",
    "WORKER_BACKEND_BASE_URL": "advanced.worker_backend_url",
    "NOTIFYHUB_ENABLED": "notifyhub.enabled",
    "NOTIFYHUB_URL": "notifyhub.url",
    "NOTIFYHUB_API_KEY": "notifyhub.api_key",
    "NOTIFYHUB_TOPIC": "notifyhub.topic",
}

# Reverse mapping for convenience
_PATH_TO_KEY: dict[str, str] = {v: k for k, v in _KEY_TO_PATH.items()}

# ---------------------------------------------------------------------------
# Schema: UI metadata for each setting (label, type, category, default)
# ---------------------------------------------------------------------------

SETTINGS_SCHEMA: dict[str, dict[str, Any]] = {
    "FLEX_TOKEN": {"category": "ibkr", "label": "Flex Token", "type": "password", "default": ""},
    "FLEX_QUERY_IDS": {"category": "ibkr", "label": "Flex Query IDs", "type": "text", "default": "1532356,1532359"},
    "FLEX_BASE_URL": {"category": "ibkr", "label": "Flex Base URL", "type": "text", "default": "https://www.interactivebrokers.com/AccountManagement/FlexWebService"},
    "FLEX_POLL_INTERVAL_SECONDS": {"category": "ibkr", "label": "Poll Interval (s)", "type": "number", "default": "10"},
    "FLEX_MAX_POLL_RETRIES": {"category": "ibkr", "label": "Max Poll Retries", "type": "number", "default": "60"},
    "LLM_API_KEY": {"category": "llm", "label": "API Key", "type": "password", "default": ""},
    "LLM_BASE_URL": {"category": "llm", "label": "Base URL", "type": "text", "default": "https://api.openai.com/v1"},
    "LLM_DEFAULT_MODEL": {"category": "llm", "label": "Default Model", "type": "text", "default": "gpt-4o"},
    "LLM_TEMPERATURE": {"category": "llm", "label": "Temperature", "type": "number", "default": "0.1"},
    "LLM_MAX_TOKENS": {"category": "llm", "label": "Max Tokens", "type": "number", "default": "8192"},
    "BLS_API_KEY": {"category": "llm", "label": "BLS API Key", "type": "password", "default": ""},
    "SCHEDULER_ENABLED": {"category": "scheduler", "label": "Enabled", "type": "boolean", "default": "true"},
    "SCHEDULER_HOUR": {"category": "scheduler", "label": "Hour", "type": "number", "default": "12"},
    "SCHEDULER_MINUTE": {"category": "scheduler", "label": "Minute", "type": "number", "default": "30"},
    "SCHEDULER_TIMEZONE": {"category": "scheduler", "label": "Timezone", "type": "text", "default": "Asia/Shanghai"},
    "MARKET_EVENTS_SYNC_INTERVAL_HOURS": {"category": "scheduler", "label": "Market Events Sync (hours)", "type": "select", "default": "24", "options": ["12", "24"]},
    "AUTH_USERNAME": {"category": "auth", "label": "Username", "type": "text", "default": "admin"},
    "AUTH_PASSWORD": {"category": "auth", "label": "Password", "type": "password", "default": ""},
    "COOKIE_SECURE": {"category": "auth", "label": "Secure Cookie", "type": "boolean", "default": "false"},
    "LONGBRIDGE_APP_KEY": {"category": "longbridge", "label": "App Key", "type": "password", "default": ""},
    "LONGBRIDGE_APP_SECRET": {"category": "longbridge", "label": "App Secret", "type": "password", "default": ""},
    "LONGBRIDGE_ACCESS_TOKEN": {"category": "longbridge", "label": "Access Token", "type": "password", "default": ""},
    "SQLITE_PATH": {"category": "advanced", "label": "SQLite Path", "type": "text", "default": "data/ibkr_dash.db"},
    "DEBUG": {"category": "advanced", "label": "Debug Mode", "type": "boolean", "default": "false"},
    "LOG_LEVEL": {"category": "advanced", "label": "Log Level", "type": "select", "default": "INFO", "options": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
    "CORS_ORIGINS": {"category": "advanced", "label": "CORS Origins", "type": "text", "default": "http://localhost:5173"},
    "DATA_DIR": {"category": "advanced", "label": "Data Directory", "type": "text", "default": "data/flex_exports"},
    "AUDIT_LLM_CALLS": {"category": "advanced", "label": "Audit LLM Calls", "type": "boolean", "default": "false"},
    "APP_NAME": {"category": "advanced", "label": "App Name", "type": "text", "default": "IBKR Dash"},
    "APP_ENV": {"category": "advanced", "label": "App Environment", "type": "select", "default": "development", "options": ["development", "staging", "production"]},
    "CACHE_TTL_SECONDS": {"category": "advanced", "label": "Cache TTL (seconds)", "type": "number", "default": "86400"},
    "WORKER_BACKEND_BASE_URL": {"category": "advanced", "label": "Worker Backend URL", "type": "text", "default": "http://localhost:8000"},
}


# ---------------------------------------------------------------------------
# Public API (used by admin routes)
# ---------------------------------------------------------------------------


def get_setting(key: str) -> str | None:
    """Get a single setting value by flat KEY name."""
    # Try direct KEY→path mapping first
    dot_path = _KEY_TO_PATH.get(key)
    if dot_path:
        val = get_manager().get(dot_path)
        return str(val) if val is not None else None
    return None


def get_setting_with_default(key: str) -> str:
    """Get a setting value, falling back to schema default."""
    val = get_setting(key)
    if val is not None:
        return val
    meta = SETTINGS_SCHEMA.get(key, {})
    return str(meta.get("default", ""))


def get_all_settings() -> dict[str, list[dict[str, Any]]]:
    """Get all settings organized by category for the admin UI.

    Returns: {category: [{key, label, value, display_value, type, default, is_set}, ...]}
    """
    mgr = get_manager()
    result: dict[str, list[dict[str, Any]]] = {}

    for key, meta in SETTINGS_SCHEMA.items():
        category = meta["category"]
        if category not in result:
            result[category] = []

        dot_path = _KEY_TO_PATH.get(key, "")
        raw_value = mgr.get(dot_path, meta["default"])
        # Normalize booleans to lowercase strings so frontend toggles work
        if isinstance(raw_value, bool):
            value = str(raw_value).lower()
        elif raw_value is not None:
            value = str(raw_value)
        else:
            value = str(meta["default"])

        # Mask passwords
        display_value = value
        if meta["type"] == "password" and value:
            display_value = value[:4] + "****" + value[-4:] if len(value) > 8 else "****"

        is_set = value != str(meta["default"]) and value != ""

        entry: dict[str, Any] = {
            "key": key,
            "label": meta["label"],
            "value": value,
            "display_value": display_value,
            "type": meta["type"],
            "default": meta["default"],
            "is_set": is_set,
        }

        # Include options for select/dropdown fields
        if "options" in meta:
            entry["options"] = meta["options"]

        result[category].append(entry)

    return result


def update_settings(payload: dict[str, str]) -> int:
    """Update multiple settings from flat KEY→value pairs.

    Returns the number of settings updated.
    """
    updates: dict[str, Any] = {}
    for key, value in payload.items():
        dot_path = _KEY_TO_PATH.get(key)
        if dot_path:
            # Coerce types based on schema
            meta = SETTINGS_SCHEMA.get(key, {})
            if meta.get("type") == "number":
                try:
                    value = float(value) if "." in str(value) else int(value)
                except (ValueError, TypeError):
                    pass
            elif meta.get("type") == "boolean":
                value = str(value).lower() in ("true", "1", "yes")
            updates[dot_path] = value
    return get_manager().update_batch(updates)


def reset_settings(keys: list[str] | None = None) -> int:
    """Reset settings to defaults.

    If keys is None, reset all.
    Returns the number of settings reset.
    """
    mgr = get_manager()
    if keys is None:
        mgr.reset_all()
        return len(SETTINGS_SCHEMA)
    count = 0
    for key in keys:
        dot_path = _KEY_TO_PATH.get(key)
        if dot_path:
            mgr.reset(dot_path)
            count += 1
    return count
