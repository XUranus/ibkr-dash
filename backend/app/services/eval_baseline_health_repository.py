"""Evaluation baseline health report repository — SQLite-backed."""

from __future__ import annotations

import json
from typing import Any

from app.core.database import Database
from app.utils.dates import utc_now_iso


class BaselineHealthReportRepository:
    """Store and query baseline health reports in SQLite."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def save_report(self, report: dict) -> dict:
        self.db.execute(
            """INSERT OR REPLACE INTO eval_baseline_health_reports
               (report_id, status, agent_name, overall_score,
                recommendations_json, signals_json, summary_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                report.get("report_id", ""),
                report.get("status", "pending"),
                report.get("agent_name", ""),
                report.get("overall_score", 0),
                json.dumps(report.get("recommendations", [])),
                json.dumps(report.get("architecture_signals", report.get("signals", []))),
                json.dumps({k: v for k, v in report.items() if k not in {
                    "report_id", "status", "agent_name", "overall_score",
                    "recommendations", "architecture_signals", "signals", "created_at",
                }}),
                report.get("created_at", report.get("generated_at", utc_now_iso())),
            ),
        )
        return report

    def get_report(self, report_id: str) -> dict | None:
        row = self.db.execute_one(
            "SELECT * FROM eval_baseline_health_reports WHERE report_id = ?",
            (report_id,),
        )
        return self._row_to_report(row) if row else None

    def list_reports(
        self,
        *,
        agent_name: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        conditions = []
        params: list[Any] = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if agent_name:
            conditions.append("agent_name = ?")
            params.append(agent_name)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(max(1, min(int(limit), 10000)))
        rows = self.db.execute(
            f"SELECT * FROM eval_baseline_health_reports{where} ORDER BY created_at DESC LIMIT ?",
            tuple(params),
        )
        return [self._row_to_report(row) for row in rows]

    @staticmethod
    def _row_to_report(row: dict) -> dict:
        summary = json.loads(row.get("summary_json") or "{}")
        return {
            "report_id": row["report_id"],
            "status": row.get("status", "pending"),
            "agent_name": row.get("agent_name", ""),
            "overall_score": row.get("overall_score", 0),
            "recommendations": json.loads(row.get("recommendations_json") or "[]"),
            "architecture_signals": json.loads(row.get("signals_json") or "[]"),
            "created_at": row.get("created_at"),
            **summary,
        }


class InMemoryBaselineHealthReportRepository:
    """In-memory version for testing."""

    def __init__(self) -> None:
        self.reports: dict[str, dict] = {}

    def save_report(self, report: dict) -> dict:
        self.reports[report["report_id"]] = dict(report)
        return report

    def get_report(self, report_id: str) -> dict | None:
        report = self.reports.get(report_id)
        return dict(report) if report else None

    def list_reports(
        self,
        *,
        agent_name: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        items = list(self.reports.values())
        if status:
            items = [item for item in items if item.get("status") == status]
        if agent_name:
            items = [
                item for item in items
                if any(row.get("agent_name") == agent_name for row in (item.get("by_agent") or []))
            ]
        items.sort(key=lambda item: item.get("generated_at") or "", reverse=True)
        return [dict(item) for item in items[:limit]]
