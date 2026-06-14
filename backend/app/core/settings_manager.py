"""JSON-backed settings manager.

Single source of truth for all application configuration.
Reads/writes a hierarchical JSON file. Thread-safe. Auto-creates from defaults.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Path to the JSON config file
_PROJECT_ROOT = Path(__file__).resolve().parents[2]  # ibkr-dash/
CONFIG_PATH = _PROJECT_ROOT / "data" / "config.json"

# ---------------------------------------------------------------------------
# Defaults — canonical structure of config.json
# ---------------------------------------------------------------------------

DEFAULTS: dict[str, Any] = {
    "ibkr": {
        "flex_token": "",
        "flex_query_ids": "1532356,1532359",
        "flex_base_url": "https://www.interactivebrokers.com/AccountManagement/FlexWebService",
        "flex_poll_interval_seconds": 10,
        "flex_max_poll_retries": 60,
    },
    "llm": {
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
        "temperature": 0.1,
        "max_tokens": 8192,
        "bls_api_key": "",
    },
    "scheduler": {
        "enabled": True,
        "hour": 12,
        "minute": 30,
        "timezone": "Asia/Shanghai",
    },
    "auth": {
        "username": "admin",
        "password": "",
        "cookie_secure": False,
    },
    "email": {
        "smtp_host": "",
        "smtp_port": 587,
        "smtp_username": "",
        "smtp_password": "",
        "from_address": "",
        "to_addresses": [],
        "enabled": False,
    },
    "longbridge": {
        "app_key": "",
        "app_secret": "",
        "access_token": "",
    },
    "advanced": {
        "app_name": "IBKR Dash",
        "app_env": "development",
        "debug": False,
        "sqlite_path": "data/ibkr_dash.db",
        "log_level": "INFO",
        "cors_origins": "http://localhost:5173",
        "data_dir": "data/flex_exports",
        "cache_ttl_seconds": 86400,
        "audit_llm_calls": False,
    },
    "worker": {
        "backend_base_url": "http://localhost:8000",
        "daily_review_internal_token": "",
    },
}


# ---------------------------------------------------------------------------
# Deep merge utility
# ---------------------------------------------------------------------------


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge *override* into *base* recursively. Returns a new dict."""
    result = deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


# ---------------------------------------------------------------------------
# SettingsManager
# ---------------------------------------------------------------------------


class SettingsManager:
    """Thread-safe JSON-backed configuration store."""

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path else CONFIG_PATH
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {}
        self._load()

    # -- persistence --------------------------------------------------------

    def _load(self) -> None:
        """Load config from disk, merging with defaults."""
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                self._data = _deep_merge(DEFAULTS, stored)
                logger.info("Loaded settings from %s", self._path)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to read %s, using defaults: %s", self._path, exc)
                self._data = deepcopy(DEFAULTS)
        else:
            self._data = deepcopy(DEFAULTS)
            self._save()
            logger.info("Created default settings at %s", self._path)

    def _save(self) -> None:
        """Persist current config to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        tmp.replace(self._path)

    # -- read ---------------------------------------------------------------

    def get(self, dot_path: str, default: Any = None) -> Any:
        """Get a value by dot-separated path, e.g. 'llm.api_key'."""
        keys = dot_path.split(".")
        with self._lock:
            node: Any = self._data
            for k in keys:
                if isinstance(node, dict) and k in node:
                    node = node[k]
                else:
                    return default
            return node

    def get_section(self, section: str) -> dict[str, Any]:
        """Get an entire section as a dict."""
        with self._lock:
            val = self._data.get(section)
            return deepcopy(val) if isinstance(val, dict) else {}

    def get_all(self) -> dict[str, Any]:
        """Return a deep copy of the full config."""
        with self._lock:
            return deepcopy(self._data)

    # -- write --------------------------------------------------------------

    def set(self, dot_path: str, value: Any) -> None:
        """Set a value by dot-separated path and persist."""
        keys = dot_path.split(".")
        with self._lock:
            node = self._data
            for k in keys[:-1]:
                if k not in node or not isinstance(node[k], dict):
                    node[k] = {}
                node = node[k]
            node[keys[-1]] = value
            self._save()

    def update_batch(self, updates: dict[str, Any]) -> int:
        """Batch-update multiple dot-path → value pairs. Returns count."""
        count = 0
        with self._lock:
            for dot_path, value in updates.items():
                keys = dot_path.split(".")
                node = self._data
                for k in keys[:-1]:
                    if k not in node or not isinstance(node[k], dict):
                        node[k] = {}
                    node = node[k]
                node[keys[-1]] = value
                count += 1
            self._save()
        return count

    def reset(self, dot_path: str) -> None:
        """Reset a single key to its default value."""
        keys = dot_path.split(".")
        default_node: Any = DEFAULTS
        for k in keys:
            if isinstance(default_node, dict) and k in default_node:
                default_node = default_node[k]
            else:
                default_node = None
                break
        self.set(dot_path, deepcopy(default_node))

    def reset_all(self) -> None:
        """Reset entire config to defaults."""
        with self._lock:
            self._data = deepcopy(DEFAULTS)
            self._save()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_manager: SettingsManager | None = None


def get_manager() -> SettingsManager:
    """Return the process-wide SettingsManager singleton."""
    global _manager
    if _manager is None:
        _manager = SettingsManager()
    return _manager


def reload_manager() -> SettingsManager:
    """Force-reload from disk (useful after external edits)."""
    global _manager
    _manager = SettingsManager()
    return _manager
