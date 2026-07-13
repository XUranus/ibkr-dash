"""Shared test helpers for Portfolio Manager domain tests.

Provides an in-memory SQLite database and factory functions for repositories.
"""

from __future__ import annotations

from app.core.database import Database, init_database


def make_test_db() -> Database:
    """Create an in-memory SQLite database with all tables initialized."""
    db = Database(":memory:")
    db.init_schema()
    return db
