"""Tests for AgentReplayService."""

import json

from app.agents.run_replay import AgentReplaySnapshot
from app.services.agent_replay_service import AgentReplayService


class FakeDB:
    """Minimal in-memory DB stub for testing."""

    def __init__(self):
        self.store: dict[str, dict] = {}

    def upsert(self, table: str, data: dict, conflict_cols=None):
        key_col = (conflict_cols or ["id"])[0]
        key = data.get(key_col, "")
        self.store[f"{table}:{key}"] = data

    def execute_one(self, sql: str, params=()):
        # Simple lookup by replay_id or run_id
        if "WHERE replay_id" in sql:
            key = f"agent_replays:{params[0]}"
            row = self.store.get(key)
            if row:
                return {"payload_json": row["payload_json"]}
        if "WHERE run_id" in sql:
            for k, v in self.store.items():
                if k.startswith("agent_replays:") and v.get("run_id") == params[0]:
                    return {"payload_json": v["payload_json"]}
        return None

    def execute(self, sql: str, params=()):
        results = []
        for k, v in self.store.items():
            if not k.startswith("agent_replays:"):
                continue
            # Simple filter matching for agent_name and final_status
            if "agent_name = ?" in sql and params:
                if v.get("agent_name") != params[0]:
                    continue
            if "final_status = ?" in sql:
                status_idx = sql.index("final_status = ?")
                # Find which param corresponds to final_status
                pre = sql[:status_idx]
                param_idx = pre.count("?")
                if param_idx < len(params) and v.get("final_status") != params[param_idx]:
                    continue
            results.append({"payload_json": v["payload_json"]})
        limit = params[-1] if params else 50
        return results[:limit]


class TestAgentReplayService:
    def test_record_and_get(self):
        db = FakeDB()
        service = AgentReplayService(db)

        snapshot = AgentReplaySnapshot(
            replay_id="test_replay_001",
            run_id="test_run_001",
            agent_name="trade_decision",
            final_status="success",
        )
        service.record_snapshot(snapshot)

        result = service.get_snapshot("test_replay_001")
        assert result is not None
        assert result["agent_name"] == "trade_decision"
        assert result["run_id"] == "test_run_001"

    def test_get_by_run_id(self):
        db = FakeDB()
        service = AgentReplayService(db)

        snapshot = AgentReplaySnapshot(
            replay_id="test_replay_002",
            run_id="test_run_002",
            agent_name="risk_assessment",
        )
        service.record_snapshot(snapshot)

        result = service.get_by_run_id("test_run_002")
        assert result is not None
        assert result["agent_name"] == "risk_assessment"

    def test_get_nonexistent(self):
        db = FakeDB()
        service = AgentReplayService(db)
        assert service.get_snapshot("nonexistent") is None
        assert service.get_by_run_id("nonexistent") is None

    def test_list_snapshots(self):
        db = FakeDB()
        service = AgentReplayService(db)

        for i in range(3):
            snapshot = AgentReplaySnapshot(
                replay_id=f"replay_{i}",
                run_id=f"run_{i}",
                agent_name="trade_decision" if i % 2 == 0 else "risk_assessment",
            )
            service.record_snapshot(snapshot)

        all_items = service.list_snapshots()
        assert len(all_items) == 3

        filtered = service.list_snapshots(agent_name="trade_decision")
        assert len(filtered) == 2

    def test_summary(self):
        db = FakeDB()
        service = AgentReplayService(db)
        items = [
            {"agent_name": "trade_decision", "final_status": "success"},
            {"agent_name": "trade_decision", "final_status": "partial"},
            {"agent_name": "risk_assessment", "final_status": "success"},
        ]
        summary = service.summary(items)
        assert summary["total"] == 3
        assert summary["by_agent"]["trade_decision"] == 2
        assert summary["by_status"]["success"] == 2

    def test_record_dict(self):
        db = FakeDB()
        service = AgentReplayService(db)

        payload = {
            "replay_id": "dict_replay_001",
            "run_id": "dict_run_001",
            "agent_name": "daily_review",
            "final_status": "success",
            "request": {"symbol": "AAPL"},
        }
        service.record_snapshot(payload)

        result = service.get_snapshot("dict_replay_001")
        assert result is not None
        assert result["agent_name"] == "daily_review"

    def test_sanitization_on_record(self):
        db = FakeDB()
        service = AgentReplayService(db)

        snapshot = AgentReplaySnapshot(
            replay_id="sanitized_001",
            run_id="run_001",
            agent_name="test",
            request={"api_key": "secret123", "symbol": "AAPL"},
        )
        service.record_snapshot(snapshot)

        result = service.get_snapshot("sanitized_001")
        assert result is not None
        assert result["request"]["api_key"] == "***"
        assert result["request"]["symbol"] == "AAPL"
