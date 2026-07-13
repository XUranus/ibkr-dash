"""Evaluation failure mining repository — SQLite-backed."""

from __future__ import annotations

import json
from typing import Any

from app.agents.eval_failure_mining import SEVERITY_ORDER
from app.core.database import Database
from app.utils.dates import utc_now_iso


class SyntheticFailureMiningRepository:
    """Store and query failure mining runs and items in SQLite."""

    def __init__(self, db: Database) -> None:
        self.db = db

    # ---- Runs ----

    def save_failure_mining_run(self, run: dict) -> dict:
        self.db.execute(
            """INSERT OR REPLACE INTO eval_failure_mining_runs
               (failure_mining_run_id, simulation_run_id, status, started_at, finished_at,
                summary_json, config_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run.get("failure_mining_run_id", ""),
                run.get("simulation_run_id", ""),
                run.get("status", "pending"),
                run.get("started_at"),
                run.get("finished_at"),
                json.dumps(run.get("summary", {})),
                json.dumps(run.get("config", {})),
                run.get("created_at", utc_now_iso()),
            ),
        )
        return run

    def get_failure_mining_run(self, failure_mining_run_id: str) -> dict | None:
        row = self.db.execute_one(
            "SELECT * FROM eval_failure_mining_runs WHERE failure_mining_run_id = ?",
            (failure_mining_run_id,),
        )
        return self._row_to_run(row) if row else None

    def list_failure_mining_runs(
        self,
        *,
        simulation_run_id: str | None = None,
        agent_name: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        conditions = []
        params: list[Any] = []
        if simulation_run_id:
            conditions.append("simulation_run_id = ?")
            params.append(simulation_run_id)
        if status:
            conditions.append("status = ?")
            params.append(status)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(max(1, min(int(limit), 10000)))
        rows = self.db.execute(
            f"SELECT * FROM eval_failure_mining_runs{where} ORDER BY started_at DESC LIMIT ?",
            tuple(params),
        )
        results = [self._row_to_run(row) for row in rows]
        if agent_name:
            results = [r for r in results if agent_name in (r.get("agent_names") or [])]
        return results

    # ---- Items ----

    def save_failure_item(self, item: dict) -> dict:
        self.db.execute(
            """INSERT OR REPLACE INTO eval_failure_items
               (failure_id, failure_mining_run_id, simulation_result_id, agent_name,
                scenario_id, severity, category, error_type, error_message,
                node_name, details_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.get("failure_id", ""),
                item.get("failure_mining_run_id", ""),
                item.get("simulation_result_id", ""),
                item.get("agent_name", ""),
                item.get("scenario_id", ""),
                item.get("severity", "medium"),
                item.get("category", ""),
                item.get("failure_type", item.get("error_type", "")),
                item.get("error_message", ""),
                item.get("node_name", ""),
                json.dumps({k: v for k, v in item.items() if k not in {
                    "failure_id", "failure_mining_run_id", "simulation_result_id",
                    "agent_name", "scenario_id", "severity", "category",
                    "failure_type", "error_type", "error_message", "node_name", "created_at",
                }}),
                item.get("created_at", utc_now_iso()),
            ),
        )
        return item

    def list_failure_items(
        self,
        *,
        failure_mining_run_id: str | None = None,
        simulation_run_id: str | None = None,
        agent_name: str | None = None,
        failure_type: str | None = None,
        min_severity: str | None = None,
        should_convert_to_eval_case: bool | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        conditions = []
        params: list[Any] = []
        if failure_mining_run_id:
            conditions.append("failure_mining_run_id = ?")
            params.append(failure_mining_run_id)
        if agent_name:
            conditions.append("agent_name = ?")
            params.append(agent_name)
        if failure_type:
            conditions.append("error_type = ?")
            params.append(failure_type)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(max(1, min(int(limit), 10000)))
        rows = self.db.execute(
            f"SELECT * FROM eval_failure_items{where} ORDER BY created_at DESC LIMIT ?",
            tuple(params),
        )
        items = [self._row_to_item(row) for row in rows]
        if simulation_run_id:
            items = [i for i in items if i.get("simulation_run_id") == simulation_run_id]
        if should_convert_to_eval_case is not None:
            items = [i for i in items if i.get("should_convert_to_eval_case") is should_convert_to_eval_case]
        return _filter_min_severity(items, min_severity)

    def get_failure_item(self, failure_id: str) -> dict | None:
        row = self.db.execute_one(
            "SELECT * FROM eval_failure_items WHERE failure_id = ?",
            (failure_id,),
        )
        return self._row_to_item(row) if row else None

    # ---- Helpers ----

    @staticmethod
    def _row_to_run(row: dict) -> dict:
        return {
            "failure_mining_run_id": row["failure_mining_run_id"],
            "simulation_run_id": row.get("simulation_run_id", ""),
            "status": row.get("status", "pending"),
            "started_at": row.get("started_at"),
            "finished_at": row.get("finished_at"),
            "summary": json.loads(row.get("summary_json") or "{}"),
            "config": json.loads(row.get("config_json") or "{}"),
            "created_at": row.get("created_at"),
        }

    @staticmethod
    def _row_to_item(row: dict) -> dict:
        details = json.loads(row.get("details_json") or "{}")
        return {
            "failure_id": row["failure_id"],
            "failure_mining_run_id": row.get("failure_mining_run_id", ""),
            "simulation_result_id": row.get("simulation_result_id", ""),
            "agent_name": row.get("agent_name", ""),
            "scenario_id": row.get("scenario_id", ""),
            "severity": row.get("severity", "medium"),
            "failure_type": row.get("error_type", ""),
            "error_message": row.get("error_message", ""),
            "node_name": row.get("node_name", ""),
            "created_at": row.get("created_at"),
            **details,
        }


class InMemorySyntheticFailureMiningRepository:
    """In-memory version for testing."""

    def __init__(self) -> None:
        self.runs: dict[str, dict] = {}
        self.items: dict[str, dict] = {}

    def save_failure_mining_run(self, run: dict) -> dict:
        self.runs[run["failure_mining_run_id"]] = dict(run)
        return run

    def get_failure_mining_run(self, failure_mining_run_id: str) -> dict | None:
        run = self.runs.get(failure_mining_run_id)
        return dict(run) if run else None

    def list_failure_mining_runs(
        self,
        *,
        simulation_run_id: str | None = None,
        agent_name: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        items = list(self.runs.values())
        if simulation_run_id:
            items = [item for item in items if item.get("simulation_run_id") == simulation_run_id]
        if agent_name:
            items = [item for item in items if agent_name in (item.get("agent_names") or [])]
        if status:
            items = [item for item in items if item.get("status") == status]
        items.sort(key=lambda item: item.get("started_at") or "", reverse=True)
        return [dict(item) for item in items[:limit]]

    def save_failure_item(self, item: dict) -> dict:
        self.items[item["failure_id"]] = dict(item)
        return item

    def list_failure_items(
        self,
        *,
        failure_mining_run_id: str | None = None,
        simulation_run_id: str | None = None,
        agent_name: str | None = None,
        failure_type: str | None = None,
        min_severity: str | None = None,
        should_convert_to_eval_case: bool | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        items = list(self.items.values())
        if failure_mining_run_id:
            items = [item for item in items if item.get("failure_mining_run_id") == failure_mining_run_id]
        if simulation_run_id:
            items = [item for item in items if item.get("simulation_run_id") == simulation_run_id]
        if agent_name:
            items = [item for item in items if item.get("agent_name") == agent_name]
        if failure_type:
            items = [item for item in items if item.get("failure_type") == failure_type]
        if should_convert_to_eval_case is not None:
            items = [item for item in items if item.get("should_convert_to_eval_case") is should_convert_to_eval_case]
        items = _filter_min_severity(items, min_severity)
        items.sort(key=lambda item: (item.get("conversion_priority") or 0, item.get("created_at") or ""), reverse=True)
        return [dict(item) for item in items[:limit]]

    def get_failure_item(self, failure_id: str) -> dict | None:
        item = self.items.get(failure_id)
        return dict(item) if item else None


def _filter_min_severity(items: list[dict], min_severity: str | None) -> list[dict]:
    if not min_severity:
        return items
    threshold = SEVERITY_ORDER.get(min_severity, 1)
    return [item for item in items if SEVERITY_ORDER.get(item.get("severity"), 0) >= threshold]
