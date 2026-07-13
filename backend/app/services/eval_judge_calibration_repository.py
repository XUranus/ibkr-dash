"""Evaluation judge calibration repository — SQLite-backed."""

from __future__ import annotations

import json
from typing import Any

from app.core.database import Database
from app.utils.dates import utc_now_iso


class JudgeCalibrationRepository:
    """Store and query judge calibration runs and signals in SQLite."""

    def __init__(self, db: Database) -> None:
        self.db = db

    # ---- Runs ----

    def save_run(self, run: dict) -> dict:
        self.db.execute(
            """INSERT OR REPLACE INTO eval_judge_calibration_runs
               (calibration_run_id, status, started_at, finished_at,
                summary_json, config_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                run.get("calibration_run_id", ""),
                run.get("status", "pending"),
                run.get("started_at"),
                run.get("finished_at"),
                json.dumps(run.get("summary", {})),
                json.dumps(run.get("config", {})),
                run.get("created_at", utc_now_iso()),
            ),
        )
        return run

    def get_run(self, calibration_run_id: str) -> dict | None:
        row = self.db.execute_one(
            "SELECT * FROM eval_judge_calibration_runs WHERE calibration_run_id = ?",
            (calibration_run_id,),
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
            f"SELECT * FROM eval_judge_calibration_runs{where} ORDER BY created_at DESC LIMIT ?",
            tuple(params),
        )
        results = [self._row_to_run(row) for row in rows]
        if agent_name:
            results = [
                r for r in results
                if agent_name in ((r.get("summary") or {}).get("by_agent") or {})
            ]
        return results

    # ---- Signals ----

    def save_signal(self, signal: dict) -> dict:
        self.db.execute(
            """INSERT OR REPLACE INTO eval_judge_calibration_signals
               (signal_id, calibration_run_id, case_id, agent_name,
                expected_label, actual_label, judge_score, correct,
                details_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                signal.get("signal_id", ""),
                signal.get("calibration_run_id", ""),
                signal.get("case_id", signal.get("scenario_id", "")),
                signal.get("agent_name", ""),
                signal.get("expected_label", ""),
                signal.get("actual_label", signal.get("judge_status", "")),
                signal.get("judge_score", 0),
                1 if signal.get("correct") else 0,
                json.dumps({k: v for k, v in signal.items() if k not in {
                    "signal_id", "calibration_run_id", "case_id", "agent_name",
                    "expected_label", "actual_label", "judge_score", "correct", "created_at",
                }}),
                signal.get("created_at", utc_now_iso()),
            ),
        )
        return signal

    def list_signals(
        self,
        *,
        calibration_run_id: str | None = None,
        agent_name: str | None = None,
        signal_type: str | None = None,
        min_priority: int | None = None,
        should_create_calibration_case: bool | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        conditions = []
        params: list[Any] = []
        if calibration_run_id:
            conditions.append("calibration_run_id = ?")
            params.append(calibration_run_id)
        if agent_name:
            conditions.append("agent_name = ?")
            params.append(agent_name)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(max(1, min(int(limit), 10000)))
        rows = self.db.execute(
            f"SELECT * FROM eval_judge_calibration_signals{where} ORDER BY created_at DESC LIMIT ?",
            tuple(params),
        )
        items = [self._row_to_signal(row) for row in rows]
        if signal_type:
            items = [i for i in items if i.get("signal_type") == signal_type]
        if min_priority is not None:
            items = [i for i in items if int(i.get("priority") or 0) >= int(min_priority)]
        if should_create_calibration_case is not None:
            items = [i for i in items if i.get("should_create_calibration_case") is should_create_calibration_case]
        return items

    def get_signal(self, signal_id: str) -> dict | None:
        row = self.db.execute_one(
            "SELECT * FROM eval_judge_calibration_signals WHERE signal_id = ?",
            (signal_id,),
        )
        return self._row_to_signal(row) if row else None

    # ---- Helpers ----

    @staticmethod
    def _row_to_run(row: dict) -> dict:
        return {
            "calibration_run_id": row["calibration_run_id"],
            "status": row.get("status", "pending"),
            "started_at": row.get("started_at"),
            "finished_at": row.get("finished_at"),
            "summary": json.loads(row.get("summary_json") or "{}"),
            "config": json.loads(row.get("config_json") or "{}"),
            "created_at": row.get("created_at"),
        }

    @staticmethod
    def _row_to_signal(row: dict) -> dict:
        details = json.loads(row.get("details_json") or "{}")
        return {
            "signal_id": row["signal_id"],
            "calibration_run_id": row.get("calibration_run_id", ""),
            "agent_name": row.get("agent_name", ""),
            "expected_label": row.get("expected_label", ""),
            "actual_label": row.get("actual_label", ""),
            "judge_score": row.get("judge_score", 0),
            "correct": bool(row.get("correct")),
            "created_at": row.get("created_at"),
            **details,
        }


class InMemoryJudgeCalibrationRepository:
    """In-memory version for testing."""

    def __init__(self) -> None:
        self.runs: dict[str, dict] = {}
        self.signals: dict[str, dict] = {}

    def save_run(self, run: dict) -> dict:
        self.runs[run["calibration_run_id"]] = dict(run)
        return run

    def get_run(self, calibration_run_id: str) -> dict | None:
        run = self.runs.get(calibration_run_id)
        return dict(run) if run else None

    def list_runs(
        self,
        *,
        agent_name: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        items = list(self.runs.values())
        if status:
            items = [item for item in items if item.get("status") == status]
        if agent_name:
            items = [
                item for item in items
                if agent_name in ((item.get("summary") or {}).get("by_agent") or {})
            ]
        items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return [dict(item) for item in items[:limit]]

    def save_signal(self, signal: dict) -> dict:
        self.signals[signal["signal_id"]] = dict(signal)
        return signal

    def list_signals(
        self,
        *,
        calibration_run_id: str | None = None,
        agent_name: str | None = None,
        signal_type: str | None = None,
        min_priority: int | None = None,
        should_create_calibration_case: bool | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        items = list(self.signals.values())
        if calibration_run_id:
            items = [item for item in items if item.get("calibration_run_id") == calibration_run_id]
        if agent_name:
            items = [item for item in items if item.get("agent_name") == agent_name]
        if signal_type:
            items = [item for item in items if item.get("signal_type") == signal_type]
        if min_priority is not None:
            items = [item for item in items if int(item.get("priority") or 0) >= int(min_priority)]
        if should_create_calibration_case is not None:
            items = [item for item in items if item.get("should_create_calibration_case") is should_create_calibration_case]
        items.sort(key=lambda item: (int(item.get("priority") or 0), item.get("created_at") or ""), reverse=True)
        return [dict(item) for item in items[:limit]]

    def get_signal(self, signal_id: str) -> dict | None:
        signal = self.signals.get(signal_id)
        return dict(signal) if signal else None
