"""SQLite-backed repository for auto-decision runs and items."""

from __future__ import annotations

from datetime import datetime

from app.core.database import Database
from app.domains.portfolio_manager.common import SQLiteDocStore, utc_now_iso
from app.domains.portfolio_manager.universe.repository import normalize_universe_symbol


class PortfolioAutoDecisionRepository:
    def __init__(self, db: Database) -> None:
        self._runs = SQLiteDocStore(db, "pm_auto_decision_runs", indexed_columns=["run_date", "run_type", "status"])
        self._items = SQLiteDocStore(
            db, "pm_auto_decision_items",
            indexed_columns=["run_id", "run_date", "symbol", "selection_status"],
        )

    def create_run(self, run_doc: dict) -> dict:
        return self._runs.put(run_doc["id"], run_doc)

    def update_run(self, run_id: str, patch: dict) -> dict | None:
        existing = self._runs.get(run_id)
        if existing is None:
            return None
        return self._runs.put(run_id, {**existing, **patch})

    def bulk_create_items(self, items: list[dict]) -> list[dict]:
        return [self._items.put(item["id"], item) for item in items]

    def update_item(self, item_id: str, patch: dict) -> dict | None:
        existing = self._items.get(item_id)
        if existing is None:
            return None
        return self._items.put(item_id, {**existing, **patch})

    def get_run(self, run_id: str) -> dict | None:
        return self._runs.get(run_id)

    def get_item(self, item_id: str) -> dict | None:
        return self._items.get(item_id)

    def list_runs(self, *, limit: int = 20, run_date: str | None = None) -> list[dict]:
        filters = {}
        if run_date:
            filters["run_date"] = run_date
        return self._runs.list_docs(filters=filters if filters else None, limit=limit)

    def list_items(self, run_id: str) -> list[dict]:
        return self._items.list_docs(filters={"run_id": run_id}, limit=1000)

    def list_symbol_history(self, symbol: str, *, limit: int = 30) -> list[dict]:
        normalized = normalize_universe_symbol(symbol)
        return self._items.list_docs(filters={"symbol": normalized}, limit=limit)

    def find_recent_completed(self, symbol: str, since_datetime: datetime) -> dict | None:
        normalized = normalize_universe_symbol(symbol)
        # Filter by symbol and selection_status, then check updated_at in Python
        items = self._items.list_docs(
            filters={"symbol": normalized, "selection_status": "completed"},
            limit=10,
        )
        for item in items:
            updated = item.get("updated_at", "")
            if updated >= since_datetime.isoformat():
                return item
        return None

    def get_latest_run(self) -> dict | None:
        runs = self.list_runs(limit=1)
        return runs[0] if runs else None
