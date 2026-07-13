"""Evaluation simulation repository — SQLite-backed."""

from __future__ import annotations

import json
from typing import Any

from app.core.database import Database
from app.utils.dates import utc_now_iso


class SyntheticSimulationRepository:
    """Store and query evaluation simulation runs and results in SQLite."""

    def __init__(self, db: Database) -> None:
        self.db = db

    # ---- Runs ----

    def save_run(self, run: dict) -> dict:
        document = dict(run)
        document.pop("results", None)
        self.db.execute(
            """INSERT OR REPLACE INTO eval_simulation_runs
               (simulation_run_id, name, status, agent_names, scenario_ids,
                started_at, finished_at, summary_json, config_json, metadata_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                document.get("simulation_run_id", ""),
                document.get("name", ""),
                document.get("status", "pending"),
                json.dumps(document.get("agent_names", [])),
                json.dumps(document.get("scenario_ids", [])),
                document.get("started_at"),
                document.get("finished_at"),
                json.dumps(document.get("summary", {})),
                json.dumps(document.get("config", {})),
                json.dumps(document.get("metadata", {})),
                document.get("created_at", utc_now_iso()),
            ),
        )
        return run

    def get_run(self, simulation_run_id: str) -> dict | None:
        row = self.db.execute_one(
            "SELECT * FROM eval_simulation_runs WHERE simulation_run_id = ?",
            (simulation_run_id,),
        )
        return self._row_to_run(row) if row else None

    def list_runs(
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
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(max(1, min(int(limit), 10000)))
        rows = self.db.execute(
            f"SELECT * FROM eval_simulation_runs{where} ORDER BY started_at DESC LIMIT ?",
            tuple(params),
        )
        results = [self._row_to_run(row) for row in rows]
        if agent_name:
            results = [r for r in results if agent_name in (r.get("agent_names") or [])]
        return results

    # ---- Results ----

    def save_result(self, result: dict) -> dict:
        self.db.execute(
            """INSERT OR REPLACE INTO eval_simulation_results
               (simulation_result_id, simulation_run_id, scenario_id, agent_name,
                status, latency_ms, error_code, source_run_id, source_task_id,
                output_json, output_summary_json, run_trace_json, node_outputs_json,
                metadata_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.get("simulation_result_id", ""),
                result.get("simulation_run_id", ""),
                result.get("scenario_id", ""),
                result.get("agent_name", ""),
                result.get("status", "pending"),
                result.get("latency_ms", 0),
                result.get("error_code", ""),
                result.get("source_run_id", ""),
                result.get("source_task_id", ""),
                json.dumps(result.get("output", {})),
                json.dumps(result.get("output_summary", {})),
                json.dumps(result.get("run_trace", {})),
                json.dumps(result.get("node_outputs", {})),
                json.dumps(result.get("metadata", {})),
                result.get("created_at", utc_now_iso()),
            ),
        )
        return result

    def list_results(self, simulation_run_id: str, limit: int = 1000) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM eval_simulation_results WHERE simulation_run_id = ? ORDER BY created_at ASC LIMIT ?",
            (simulation_run_id, max(1, min(int(limit), 10000))),
        )
        return [self._row_to_result(row) for row in rows]

    def get_result(self, simulation_result_id: str) -> dict | None:
        row = self.db.execute_one(
            "SELECT * FROM eval_simulation_results WHERE simulation_result_id = ?",
            (simulation_result_id,),
        )
        return self._row_to_result(row) if row else None

    # ---- Helpers ----

    @staticmethod
    def _row_to_run(row: dict) -> dict:
        return {
            "simulation_run_id": row["simulation_run_id"],
            "name": row.get("name", ""),
            "status": row.get("status", "pending"),
            "agent_names": json.loads(row.get("agent_names") or "[]"),
            "scenario_ids": json.loads(row.get("scenario_ids") or "[]"),
            "started_at": row.get("started_at"),
            "finished_at": row.get("finished_at"),
            "summary": json.loads(row.get("summary_json") or "{}"),
            "config": json.loads(row.get("config_json") or "{}"),
            "metadata": json.loads(row.get("metadata_json") or "{}"),
            "created_at": row.get("created_at"),
        }

    @staticmethod
    def _row_to_result(row: dict) -> dict:
        return {
            "simulation_result_id": row["simulation_result_id"],
            "simulation_run_id": row.get("simulation_run_id", ""),
            "scenario_id": row.get("scenario_id", ""),
            "agent_name": row.get("agent_name", ""),
            "status": row.get("status", "pending"),
            "latency_ms": row.get("latency_ms", 0),
            "error_code": row.get("error_code", ""),
            "source_run_id": row.get("source_run_id", ""),
            "source_task_id": row.get("source_task_id", ""),
            "output": json.loads(row.get("output_json") or "{}"),
            "output_summary": json.loads(row.get("output_summary_json") or "{}"),
            "run_trace": json.loads(row.get("run_trace_json") or "{}"),
            "node_outputs": json.loads(row.get("node_outputs_json") or "{}"),
            "metadata": json.loads(row.get("metadata_json") or "{}"),
            "created_at": row.get("created_at"),
        }


class InMemorySyntheticSimulationRepository:
    """In-memory version for testing."""

    def __init__(self) -> None:
        self.runs: dict[str, dict] = {}
        self.results: dict[str, dict] = {}

    def save_run(self, run: dict) -> dict:
        self.runs[run["simulation_run_id"]] = dict(run)
        return run

    def get_run(self, simulation_run_id: str) -> dict | None:
        run = self.runs.get(simulation_run_id)
        return dict(run) if run else None

    def list_runs(
        self,
        *,
        agent_name: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        items = list(self.runs.values())
        if agent_name:
            items = [item for item in items if agent_name in (item.get("agent_names") or [])]
        if status:
            items = [item for item in items if item.get("status") == status]
        items.sort(key=lambda item: item.get("started_at") or "", reverse=True)
        return [dict(item) for item in items[:limit]]

    def save_result(self, result: dict) -> dict:
        self.results[result["simulation_result_id"]] = dict(result)
        return result

    def list_results(self, simulation_run_id: str, limit: int = 1000) -> list[dict]:
        items = [item for item in self.results.values() if item.get("simulation_run_id") == simulation_run_id]
        items.sort(key=lambda item: item.get("created_at") or "")
        return [dict(item) for item in items[:limit]]

    def get_result(self, simulation_result_id: str) -> dict | None:
        result = self.results.get(simulation_result_id)
        return dict(result) if result else None
