"""SQLite-backed repository for improvement reports."""

from __future__ import annotations

from app.core.database import Database
from app.domains.portfolio_manager.common import SQLiteDocStore


class PortfolioImprovementRepository:
    def __init__(self, db: Database) -> None:
        self._store = SQLiteDocStore(db, "pm_improvement_reports", indexed_columns=["report_date", "report_type", "status"])

    def create_report(self, report_doc: dict) -> dict:
        return self._store.put(report_doc["id"], report_doc)

    def get_report(self, report_id: str) -> dict | None:
        return self._store.get(report_id)

    def list_reports(self, *, limit: int = 20, report_date: str | None = None) -> list[dict]:
        filters = {}
        if report_date:
            filters["report_date"] = report_date
        return self._store.list_docs(filters=filters if filters else None, limit=limit)

    def get_latest_report(self) -> dict | None:
        reports = self.list_reports(limit=1)
        return reports[0] if reports else None
