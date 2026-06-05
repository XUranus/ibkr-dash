"""Shared test fixtures."""

from __future__ import annotations

import pytest

import app.core.database as db_mod
from app.core.config import Settings
from app.core.database import Database, init_database


@pytest.fixture(autouse=True)
def _reset_db_singleton():
    """Reset the database singleton before each test."""
    db_mod._db_instance = None
    yield
    db_mod._db_instance = None


@pytest.fixture
def settings() -> Settings:
    """Return test settings with in-memory SQLite."""
    return Settings(
        sqlite_path=":memory:",
        debug=True,
        auth_password="",
    )


@pytest.fixture
def db(settings: Settings) -> Database:
    """Return an initialized in-memory database."""
    return init_database(settings)
