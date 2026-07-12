"""SQLite-backed repositories for the eval system (cases, runs, feedback)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.database import Database


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


class EvalCaseRepository:
    """Stores evaluation test cases in SQLite."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def save_case(self, case: dict) -> dict:
        case_id = case.get("case_id") or str(uuid.uuid4())
        now = _now_iso()
        data = {
            "case_id": case_id,
            "agent_name": case.get("agent_name", ""),
            "source": case.get("source", "manual"),
            "title": case.get("title", ""),
            "description": case.get("description", ""),
            "notes": case.get("notes", ""),
            "tags": _json_dumps(case.get("tags", [])),
            "enabled": 1 if case.get("enabled", True) else 0,
            "severity": case.get("severity", "medium"),
            "category": case.get("category", ""),
            "eval_scope": case.get("eval_scope", "agent"),
            "node_name": case.get("node_name", ""),
            "prompt_key": case.get("prompt_key", ""),
            "prompt_version": case.get("prompt_version", ""),
            "prompt_hash": case.get("prompt_hash", ""),
            "model": case.get("model", ""),
            "source_replay_id": case.get("source_replay_id", ""),
            "source_run_id": case.get("source_run_id", ""),
            "source_llm_call_id": case.get("source_llm_call_id", ""),
            "archived": 1 if case.get("archived") else 0,
            "archived_at": case.get("archived_at"),
            "archived_reason": case.get("archived_reason", ""),
            "input_json": _json_dumps(case.get("input", {})),
            "expected_json": _json_dumps(case.get("expected", {})),
            "metadata_json": _json_dumps(case.get("metadata", {})),
            "updated_at": now,
        }
        self.db.upsert("eval_cases", data, ["case_id"])
        return case

    def get_case(self, case_id: str) -> dict | None:
        row = self.db.execute_one("SELECT * FROM eval_cases WHERE case_id = ?", (case_id,))
        return self._row_to_case(row) if row else None

    def list_cases(
        self,
        *,
        agent_name: str | None = None,
        source: str | None = None,
        enabled: bool | None = None,
        severity: str | None = None,
        category: str | None = None,
        tag: str | None = None,
        eval_scope: str | None = None,
        node_name: str | None = None,
        source_run_id: str | None = None,
        prompt_key: str | None = None,
        model: str | None = None,
        include_archived: bool = False,
        query: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        conditions: list[str] = []
        params: list[Any] = []
        if agent_name:
            conditions.append("agent_name = ?")
            params.append(agent_name)
        if source:
            conditions.append("source = ?")
            params.append(source)
        if enabled is not None:
            conditions.append("enabled = ?")
            params.append(1 if enabled else 0)
        if not include_archived:
            conditions.append("archived = 0")
        if severity:
            conditions.append("severity = ?")
            params.append(severity)
        if category:
            conditions.append("category = ?")
            params.append(category)
        if eval_scope:
            if eval_scope == "agent":
                conditions.append("(eval_scope = 'agent' OR eval_scope = '' OR eval_scope IS NULL)")
            else:
                conditions.append("eval_scope = ?")
                params.append(eval_scope)
        if node_name:
            conditions.append("node_name = ?")
            params.append(node_name)
        if source_run_id:
            conditions.append("source_run_id = ?")
            params.append(source_run_id)
        if prompt_key:
            conditions.append("prompt_key = ?")
            params.append(prompt_key)
        if model:
            conditions.append("model = ?")
            params.append(model)
        if query:
            conditions.append("(title LIKE ? OR case_id LIKE ? OR description LIKE ? OR notes LIKE ?)")
            q = f"%{query}%"
            params.extend([q, q, q, q])
        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)
        rows = self.db.execute(
            f"SELECT * FROM eval_cases WHERE {where} ORDER BY created_at DESC LIMIT ?",
            tuple(params),
        )
        cases = [self._row_to_case(r) for r in rows]
        if tag:
            cases = [c for c in cases if tag in (c.get("tags") or [])]
        return cases

    def seed_builtin_cases(self, *, force: bool = False) -> dict:
        from app.agents.eval_cases import list_builtin_eval_cases

        created = []
        skipped = []
        for case in list_builtin_eval_cases():
            existing = self.get_case(case.case_id)
            if existing and not force:
                skipped.append(case.case_id)
                continue
            self.save_case(case.to_dict())
            created.append(case.case_id)
        return {"created": created, "skipped": skipped, "created_count": len(created), "skipped_count": len(skipped)}

    def _row_to_case(self, row: dict) -> dict:
        return {
            "case_id": row["case_id"],
            "agent_name": row.get("agent_name", ""),
            "source": row.get("source", "manual"),
            "title": row.get("title", ""),
            "description": row.get("description", ""),
            "notes": row.get("notes", ""),
            "tags": json.loads(row.get("tags") or "[]"),
            "enabled": bool(row.get("enabled", 1)),
            "severity": row.get("severity", "medium"),
            "category": row.get("category", ""),
            "eval_scope": row.get("eval_scope", "agent"),
            "node_name": row.get("node_name", ""),
            "prompt_key": row.get("prompt_key", ""),
            "prompt_version": row.get("prompt_version", ""),
            "prompt_hash": row.get("prompt_hash", ""),
            "model": row.get("model", ""),
            "source_replay_id": row.get("source_replay_id", ""),
            "source_run_id": row.get("source_run_id", ""),
            "source_llm_call_id": row.get("source_llm_call_id", ""),
            "archived": bool(row.get("archived", 0)),
            "archived_at": row.get("archived_at"),
            "archived_reason": row.get("archived_reason", ""),
            "input": json.loads(row.get("input_json") or "{}"),
            "expected": json.loads(row.get("expected_json") or "{}"),
            "metadata": json.loads(row.get("metadata_json") or "{}"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }


class EvalRunRepository:
    """Stores evaluation run results in SQLite."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def save_run(self, run: dict) -> dict:
        run_id = run.get("eval_run_id") or str(uuid.uuid4())
        data = {
            "eval_run_id": run_id,
            "name": run.get("name", ""),
            "agent_name": run.get("agent_name", ""),
            "case_ids": _json_dumps(run.get("case_ids", [])),
            "started_at": run.get("started_at"),
            "finished_at": run.get("finished_at"),
            "status": run.get("status", "pending"),
            "summary_json": _json_dumps(run.get("summary", {})),
            "results_json": _json_dumps(run.get("results", [])),
            "config_json": _json_dumps(run.get("config", {})),
        }
        self.db.upsert("eval_runs", data, ["eval_run_id"])
        return run

    def get_run(self, eval_run_id: str) -> dict | None:
        row = self.db.execute_one("SELECT * FROM eval_runs WHERE eval_run_id = ?", (eval_run_id,))
        return self._row_to_run(row) if row else None

    def list_runs(self, *, hours: int = 24, agent_name: str | None = None, limit: int = 100) -> list[dict]:
        from datetime import timedelta

        since = (datetime.now(timezone.utc) - timedelta(hours=max(1, hours))).isoformat()
        conditions = ["started_at >= ?"]
        params: list[Any] = [since]
        if agent_name:
            conditions.append("agent_name = ?")
            params.append(agent_name)
        where = " AND ".join(conditions)
        params.append(limit)
        rows = self.db.execute(
            f"SELECT * FROM eval_runs WHERE {where} ORDER BY started_at DESC LIMIT ?",
            tuple(params),
        )
        return [self._row_to_run(r) for r in rows]

    def _row_to_run(self, row: dict) -> dict:
        return {
            "eval_run_id": row["eval_run_id"],
            "name": row.get("name", ""),
            "agent_name": row.get("agent_name", ""),
            "case_ids": json.loads(row.get("case_ids") or "[]"),
            "started_at": row.get("started_at"),
            "finished_at": row.get("finished_at"),
            "status": row.get("status", "pending"),
            "summary": json.loads(row.get("summary_json") or "{}"),
            "results": json.loads(row.get("results_json") or "[]"),
            "config": json.loads(row.get("config_json") or "{}"),
            "created_at": row.get("created_at"),
        }


class BadCaseFeedbackRepository:
    """Stores bad case feedback in SQLite."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def save_feedback(self, feedback: dict) -> dict:
        fid = feedback.get("feedback_id") or str(uuid.uuid4())
        now = _now_iso()
        data = {
            "feedback_id": fid,
            "source_type": feedback.get("source_type", ""),
            "source_id": feedback.get("source_id", ""),
            "agent_name": feedback.get("agent_name", ""),
            "issue_type": feedback.get("issue_type", ""),
            "severity": feedback.get("severity", "medium"),
            "category": feedback.get("category", ""),
            "tags": _json_dumps(feedback.get("tags", [])),
            "status": feedback.get("status", "open"),
            "replay_id": feedback.get("replay_id", ""),
            "run_id": feedback.get("run_id", ""),
            "eval_run_id": feedback.get("eval_run_id", ""),
            "case_id": feedback.get("case_id", ""),
            "result_case_id": feedback.get("result_case_id", ""),
            "converted_case_id": feedback.get("converted_case_id", ""),
            "title": feedback.get("title", ""),
            "description": feedback.get("description", ""),
            "notes": feedback.get("notes", ""),
            "evidence_json": _json_dumps(feedback.get("evidence", {})),
            "metadata_json": _json_dumps(feedback.get("metadata", {})),
            "updated_at": now,
        }
        self.db.upsert("eval_feedback", data, ["feedback_id"])
        return feedback

    def get_feedback(self, feedback_id: str) -> dict | None:
        row = self.db.execute_one("SELECT * FROM eval_feedback WHERE feedback_id = ?", (feedback_id,))
        return self._row_to_feedback(row) if row else None

    def list_feedback(
        self,
        *,
        status: str | None = None,
        source_type: str | None = None,
        agent_name: str | None = None,
        severity: str | None = None,
        category: str | None = None,
        issue_type: str | None = None,
        eval_run_id: str | None = None,
        query: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        conditions: list[str] = []
        params: list[Any] = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if source_type:
            conditions.append("source_type = ?")
            params.append(source_type)
        if agent_name:
            conditions.append("agent_name = ?")
            params.append(agent_name)
        if severity:
            conditions.append("severity = ?")
            params.append(severity)
        if category:
            conditions.append("category = ?")
            params.append(category)
        if issue_type:
            conditions.append("issue_type = ?")
            params.append(issue_type)
        if eval_run_id:
            conditions.append("eval_run_id = ?")
            params.append(eval_run_id)
        if query:
            conditions.append("(title LIKE ? OR feedback_id LIKE ? OR description LIKE ? OR notes LIKE ?)")
            q = f"%{query}%"
            params.extend([q, q, q, q])
        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)
        rows = self.db.execute(
            f"SELECT * FROM eval_feedback WHERE {where} ORDER BY created_at DESC LIMIT ?",
            tuple(params),
        )
        return [self._row_to_feedback(r) for r in rows]

    def _row_to_feedback(self, row: dict) -> dict:
        return {
            "feedback_id": row["feedback_id"],
            "source_type": row.get("source_type", ""),
            "source_id": row.get("source_id", ""),
            "agent_name": row.get("agent_name", ""),
            "issue_type": row.get("issue_type", ""),
            "severity": row.get("severity", "medium"),
            "category": row.get("category", ""),
            "tags": json.loads(row.get("tags") or "[]"),
            "status": row.get("status", "open"),
            "replay_id": row.get("replay_id", ""),
            "run_id": row.get("run_id", ""),
            "eval_run_id": row.get("eval_run_id", ""),
            "case_id": row.get("case_id", ""),
            "result_case_id": row.get("result_case_id", ""),
            "converted_case_id": row.get("converted_case_id", ""),
            "title": row.get("title", ""),
            "description": row.get("description", ""),
            "notes": row.get("notes", ""),
            "evidence": json.loads(row.get("evidence_json") or "{}"),
            "metadata": json.loads(row.get("metadata_json") or "{}"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }


class RegressionProfileRepository:
    """Stores regression test profiles in SQLite."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def save_profile(self, profile: dict) -> dict:
        pid = profile.get("profile_id") or str(uuid.uuid4())
        now = _now_iso()
        data = {
            "profile_id": pid,
            "agent_name": profile.get("agent_name", ""),
            "enabled": 1 if profile.get("enabled", True) else 0,
            "mode": profile.get("mode", "full"),
            "case_tag": profile.get("case_tag", ""),
            "severity": profile.get("severity", ""),
            "category": profile.get("category", ""),
            "include_disabled": 1 if profile.get("include_disabled") else 0,
            "include_judge": 1 if profile.get("include_judge", True) else 0,
            "include_node_eval": 1 if profile.get("include_node_eval") else 0,
            "node_name": profile.get("node_name", ""),
            "limit_count": profile.get("limit", 100),
            "gate_json": _json_dumps(profile.get("gate", {})),
            "trigger_policy_json": _json_dumps(profile.get("trigger_policy", {})),
            "notes": profile.get("notes", ""),
            "version": profile.get("version", 1),
            "updated_at": now,
        }
        self.db.upsert("eval_regression_profiles", data, ["profile_id"])
        return profile

    def get_profile(self, profile_id: str) -> dict | None:
        row = self.db.execute_one("SELECT * FROM eval_regression_profiles WHERE profile_id = ?", (profile_id,))
        return self._row_to_profile(row) if row else None

    def list_profiles(self, *, enabled: bool | None = None, agent_name: str | None = None, limit: int = 100) -> list[dict]:
        conditions: list[str] = []
        params: list[Any] = []
        if enabled is not None:
            conditions.append("enabled = ?")
            params.append(1 if enabled else 0)
        if agent_name:
            conditions.append("agent_name = ?")
            params.append(agent_name)
        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)
        rows = self.db.execute(
            f"SELECT * FROM eval_regression_profiles WHERE {where} ORDER BY updated_at DESC LIMIT ?",
            tuple(params),
        )
        return [self._row_to_profile(r) for r in rows]

    def delete_profile(self, profile_id: str) -> bool:
        with self.db.get_conn() as conn:
            cursor = conn.execute("DELETE FROM eval_regression_profiles WHERE profile_id = ?", (profile_id,))
            return cursor.rowcount > 0

    def _row_to_profile(self, row: dict) -> dict:
        return {
            "profile_id": row["profile_id"],
            "agent_name": row.get("agent_name", ""),
            "enabled": bool(row.get("enabled", 1)),
            "mode": row.get("mode", "full"),
            "case_tag": row.get("case_tag", ""),
            "severity": row.get("severity", ""),
            "category": row.get("category", ""),
            "include_disabled": bool(row.get("include_disabled", 0)),
            "include_judge": bool(row.get("include_judge", 1)),
            "include_node_eval": bool(row.get("include_node_eval", 0)),
            "node_name": row.get("node_name", ""),
            "limit": row.get("limit_count", 100),
            "gate": json.loads(row.get("gate_json") or "{}"),
            "trigger_policy": json.loads(row.get("trigger_policy_json") or "{}"),
            "notes": row.get("notes", ""),
            "version": row.get("version", 1),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }


class RegressionGateReportRepository:
    """Stores regression gate reports in SQLite."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def save_report(self, report: dict) -> dict:
        rid = report.get("report_id") or str(uuid.uuid4())
        data = {
            "report_id": rid,
            "mode": report.get("mode", ""),
            "trigger_source": report.get("trigger", ""),
            "status": report.get("status", "pending"),
            "ok": 1 if report.get("ok") else 0,
            "dry_run": 1 if report.get("dry_run") else 0,
            "base_ref": report.get("base_ref", ""),
            "head_ref": report.get("head_ref", ""),
            "changed_files": _json_dumps(report.get("changed_files", [])),
            "impacted_agents": _json_dumps(report.get("impacted_agents", [])),
            "recommended_agents": _json_dumps(report.get("recommended_agents", [])),
            "executed_agents": _json_dumps(report.get("executed_agents", [])),
            "summary_json": _json_dumps(report.get("summary", {})),
            "impact_analysis_json": _json_dumps(report.get("impact_analysis", {})),
            "runs_json": _json_dumps(report.get("runs", [])),
            "reasons": _json_dumps(report.get("reasons", [])),
            "git_json": _json_dumps(report.get("git", {})),
            "metadata_json": _json_dumps(report.get("metadata", {})),
            "created_by": report.get("created_by", ""),
        }
        self.db.upsert("eval_regression_gate_reports", data, ["report_id"])
        return report

    def get_report(self, report_id: str) -> dict | None:
        row = self.db.execute_one("SELECT * FROM eval_regression_gate_reports WHERE report_id = ?", (report_id,))
        return self._row_to_report(row) if row else None

    def list_reports(
        self,
        *,
        status: str | None = None,
        trigger: str | None = None,
        ok: bool | None = None,
        dry_run: bool | None = None,
        hours: int = 24 * 30,
        limit: int = 100,
    ) -> list[dict]:
        from datetime import timedelta

        since = (datetime.now(timezone.utc) - timedelta(hours=max(1, hours))).isoformat()
        conditions = ["created_at >= ?"]
        params: list[Any] = [since]
        if status:
            conditions.append("status = ?")
            params.append(status)
        if trigger:
            conditions.append("trigger_source = ?")
            params.append(trigger)
        if ok is not None:
            conditions.append("ok = ?")
            params.append(1 if ok else 0)
        if dry_run is not None:
            conditions.append("dry_run = ?")
            params.append(1 if dry_run else 0)
        where = " AND ".join(conditions)
        params.append(limit)
        rows = self.db.execute(
            f"SELECT * FROM eval_regression_gate_reports WHERE {where} ORDER BY created_at DESC LIMIT ?",
            tuple(params),
        )
        return [self._row_to_report(r) for r in rows]

    def _row_to_report(self, row: dict) -> dict:
        return {
            "report_id": row["report_id"],
            "mode": row.get("mode", ""),
            "trigger": row.get("trigger_source", ""),
            "status": row.get("status", "pending"),
            "ok": bool(row.get("ok", 0)),
            "dry_run": bool(row.get("dry_run", 0)),
            "base_ref": row.get("base_ref", ""),
            "head_ref": row.get("head_ref", ""),
            "changed_files": json.loads(row.get("changed_files") or "[]"),
            "impacted_agents": json.loads(row.get("impacted_agents") or "[]"),
            "recommended_agents": json.loads(row.get("recommended_agents") or "[]"),
            "executed_agents": json.loads(row.get("executed_agents") or "[]"),
            "summary": json.loads(row.get("summary_json") or "{}"),
            "impact_analysis": json.loads(row.get("impact_analysis_json") or "{}"),
            "runs": json.loads(row.get("runs_json") or "[]"),
            "reasons": json.loads(row.get("reasons") or "[]"),
            "git": json.loads(row.get("git_json") or "{}"),
            "metadata": json.loads(row.get("metadata_json") or "{}"),
            "created_by": row.get("created_by", ""),
            "created_at": row.get("created_at"),
        }
