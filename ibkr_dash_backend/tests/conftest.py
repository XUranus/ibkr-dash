"""Shared test fixtures."""

from __future__ import annotations

import pytest

import app.core.config as config_mod
import app.core.database as db_mod
from app.core.config import Settings
from app.core.database import Database, init_database


@pytest.fixture(autouse=True)
def _reset_singletons(monkeypatch):
    """Reset database and settings singletons before each test."""
    db_mod._db_instance = None
    config_mod.get_settings.cache_clear()

    # Ensure auth is disabled and DB is in-memory for all tests
    monkeypatch.setenv("SQLITE_PATH", ":memory:")
    monkeypatch.setenv("AUTH_PASSWORD", "")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.example.com/v1")
    monkeypatch.setenv("LLM_DEFAULT_MODEL", "test-model")

    yield

    db_mod._db_instance = None
    config_mod.get_settings.cache_clear()


@pytest.fixture
def settings() -> Settings:
    """Return test settings with in-memory SQLite."""
    return Settings(
        sqlite_path=":memory:",
        debug=True,
        auth_password="",
        llm_api_key="test-key",
        llm_base_url="https://api.example.com/v1",
        llm_default_model="test-model",
    )


@pytest.fixture
def db(settings: Settings) -> Database:
    """Return an initialized in-memory database."""
    return init_database(settings)
