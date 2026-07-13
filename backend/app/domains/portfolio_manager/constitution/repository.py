"""SQLite-backed repository for investment constitution."""

from __future__ import annotations

from app.core.database import Database
from app.domains.portfolio_manager.common import SQLiteDocStore, utc_now_iso  # noqa: F401 — re-exported for service imports


class PortfolioConstitutionRepository:
    def __init__(self, db: Database) -> None:
        self._store = SQLiteDocStore(db, "pm_constitution")

    def get_current(self) -> dict | None:
        return self._store.get("default")

    def upsert_current(self, payload: dict) -> dict:
        return self._store.put("default", payload)

    def reset_default(self, payload: dict) -> dict:
        return self._store.put("default", payload)

    def list_versions(self, limit: int = 20) -> list[dict]:
        return self._store.list_docs(limit=limit)
