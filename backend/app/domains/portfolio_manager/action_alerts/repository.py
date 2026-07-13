"""SQLite-backed repository for action alerts."""

from __future__ import annotations

from app.core.database import Database
from app.domains.portfolio_manager.common import SQLiteDocStore, utc_now_iso


class PortfolioActionAlertRepository:
    def __init__(self, db: Database) -> None:
        self._store = SQLiteDocStore(
            db, "pm_action_alerts",
            indexed_columns=["run_date", "symbol", "alert_type", "status"],
        )

    def create_alert(self, doc: dict) -> dict:
        return self._store.put(doc["id"], doc)

    def upsert_alert(self, doc: dict) -> dict:
        return self._store.put(doc["id"], doc)

    def get_alert(self, alert_id: str) -> dict | None:
        return self._store.get(alert_id)

    def list_alerts(
        self,
        *,
        limit: int = 50,
        run_date: str | None = None,
        symbol: str | None = None,
        status: str | None = None,
        alert_type: str | None = None,
    ) -> list[dict]:
        filters: dict[str, str | None] = {}
        if run_date:
            filters["run_date"] = run_date
        if symbol:
            filters["symbol"] = symbol.upper()
        if status:
            filters["status"] = status
        if alert_type:
            filters["alert_type"] = alert_type
        return self._store.list_docs(filters=filters if filters else None, limit=limit)

    def find_existing_alert(
        self,
        *,
        run_date: str,
        symbol: str,
        alert_type: str,
        decision_id: str | None = None,
        daily_loop_run_id: str | None = None,
    ) -> dict | None:
        alerts = self.list_alerts(run_date=run_date, symbol=symbol, alert_type=alert_type, limit=20)
        for doc in alerts:
            linked = doc.get("linked_ids") or {}
            if decision_id and linked.get("decision_id") == decision_id:
                return doc
            if not decision_id and daily_loop_run_id and linked.get("daily_loop_run_id") == daily_loop_run_id:
                return doc
        return None

    def mark_sent(self, alert_id: str, *, email_subject: str, sent_at: str) -> dict | None:
        return self._patch(alert_id, {"status": "sent", "email_subject": email_subject, "email_sent_at": sent_at, "email_error": None})

    def mark_failed(self, alert_id: str, error_message: str) -> dict | None:
        return self._patch(alert_id, {"status": "failed", "email_error": error_message})

    def mark_skipped(self, alert_id: str, reason: str) -> dict | None:
        return self._patch(alert_id, {"status": "skipped", "email_error": reason})

    def _patch(self, alert_id: str, patch: dict) -> dict | None:
        existing = self.get_alert(alert_id)
        if existing is None:
            return None
        return self._store.put(alert_id, {**existing, **patch})
