"""Shared test fixtures for worker tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add the backend to the path so we can import its database module
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.core.database import Database, init_database
from worker.core.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(sqlite_path=":memory:", data_dir="/tmp/test_flex")


@pytest.fixture
def db(settings: Settings) -> Database:
    """Return an initialized in-memory database (reusing backend schema)."""
    return init_database(settings)
