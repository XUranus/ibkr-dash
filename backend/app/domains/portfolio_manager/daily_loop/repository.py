"""SQLite-backed repository for daily loop runs."""

from __future__ import annotations

from app.core.database import Database
from app.domains.portfolio_manager.common import SQLiteDocStore, utc_now_iso


class PortfolioDailyLoopRepository:
    def __init__(self, db: Database) -> None:
        self._store = SQLiteDocStore(db, "pm_daily_loop_runs", indexed_columns=["run_date", "run_type", "status", "task_id"])

    def create_run(self, run_doc: dict) -> dict:
        return self._store.put(run_doc["id"], run_doc)

    def update_run(self, run_id: str, patch: dict) -> dict | None:
        existing = self._store.get(run_id)
        if existing is None:
            return None
        return self._store.put(run_id, {**existing, **patch})

    def get_run(self, run_id: str) -> dict | None:
        return self._store.get(run_id)

    def list_runs(self, *, limit: int = 20, run_date: str | None = None) -> list[dict]:
        filters = {}
        if run_date:
            filters["run_date"] = run_date
        return self._store.list_docs(filters=filters if filters else None, limit=limit)

    def get_latest_run(self) -> dict | None:
        runs = self.list_runs(limit=1)
        return runs[0] if runs else None
