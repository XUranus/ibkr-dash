"""Shared test fixtures."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

import app.core.config as config_mod
import app.core.database as db_mod
import app.core.settings_manager as sm_mod
from app.core.config import Settings
from app.core.database import Database, init_database
from app.core.settings_manager import SettingsManager


@pytest.fixture(autouse=True)
def _reset_singletons(tmp_path):
    """Reset database and settings singletons before each test.

    Creates a fresh temp JSON config for each test so tests are isolated.
    """
    # Write test defaults to a temp config file
    test_config = {
        "ibkr": {"flex_token": "", "flex_query_ids": ""},
        "llm": {
            "api_key": "test-key",
            "base_url": "https://api.example.com/v1",
            "default_model": "test-model",
        },
        "auth": {"username": "admin", "password": "", "cookie_secure": False},
        "advanced": {
            "sqlite_path": ":memory:",
            "debug": True,
        },
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(test_config), encoding="utf-8")

    # Replace the global settings manager with one pointing to the temp file
    sm_mod._manager = SettingsManager(config_file)
    config_mod._settings = None  # reset Settings singleton
    db_mod._db_instance = None  # reset DB singleton

    yield

    db_mod._db_instance = None
    sm_mod._manager = None
    config_mod._settings = None


@pytest.fixture
def settings() -> Settings:
    """Return test settings with in-memory SQLite."""
    return Settings()


@pytest.fixture
def db(settings: Settings) -> Database:
    """Return an initialized in-memory database."""
    return init_database(settings)
