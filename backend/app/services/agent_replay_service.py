"""Agent Replay Service — store and retrieve agent run replay snapshots.

Provides CRUD for AgentReplaySnapshot using SQLite via the shared Database helper.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.run_replay import AgentReplaySnapshot, sanitize_replay_payload

logger = logging.getLogger(__name__)


class AgentReplayService:
    """Store and query agent replay snapshots in SQLite."""

    def __init__(self, db: Any) -> None:
        self.db = db

    def record_snapshot(self, snapshot: AgentReplaySnapshot | dict) -> dict:
        """Save a replay snapshot. Returns the saved document."""
        payload = snapshot.to_dict() if isinstance(snapshot, AgentReplaySnapshot) else sanitize_replay_payload(snapshot)
        replay_id = payload.get("replay_id", "")
        run_id = payload.get("run_id", "")
        agent_name = payload.get("agent_name", "")
        final_status = payload.get("final_status", "success")
        created_at = payload.get("created_at", "")

        self.db.upsert("agent_replays", {
            "replay_id": replay_id,
            "run_id": run_id,
            "agent_name": agent_name,
            "final_status": final_status,
            "created_at": created_at,
            "payload_json": json.dumps(payload, ensure_ascii=False, default=str),
        }, conflict_cols=["replay_id"])
        return payload

    def get_snapshot(self, replay_id: str) -> dict | None:
        """Get a replay snapshot by replay_id."""
        row = self.db.execute_one(
            "SELECT payload_json FROM agent_replays WHERE replay_id = ?",
            (replay_id,),
        )
        if not row:
            return None
        try:
            return json.loads(row["payload_json"])
        except (json.JSONDecodeError, KeyError):
            return None

    def get_by_run_id(self, run_id: str) -> dict | None:
        """Get a replay snapshot by run_id."""
        row = self.db.execute_one(
            "SELECT payload_json FROM agent_replays WHERE run_id = ?",
            (run_id,),
        )
        if not row:
            return None
        try:
            return json.loads(row["payload_json"])
        except (json.JSONDecodeError, KeyError):
            return None

    def list_snapshots(
        self,
        *,
        agent_name: str | None = None,
        final_status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """List replay snapshots with optional filters."""
        conditions = []
        params: list[Any] = []
        if agent_name:
            conditions.append("agent_name = ?")
            params.append(agent_name)
        if final_status:
            conditions.append("final_status = ?")
            params.append(final_status)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)
        rows = self.db.execute(
            f"SELECT payload_json FROM agent_replays {where} ORDER BY created_at DESC LIMIT ?",
            tuple(params),
        )
        results = []
        for row in rows:
            try:
                results.append(json.loads(row["payload_json"]))
            except (json.JSONDecodeError, KeyError):
                continue
        return results

    def summary(self, items: list[dict]) -> dict[str, Any]:
        """Build summary stats from a list of replay snapshots."""
        count = len(items)
        agents = {}
        statuses = {}
        for item in items:
            agent = item.get("agent_name", "unknown")
            status = item.get("final_status", "unknown")
            agents[agent] = agents.get(agent, 0) + 1
            statuses[status] = statuses.get(status, 0) + 1
        return {
            "total": count,
            "by_agent": agents,
            "by_status": statuses,
        }


__all__ = ["AgentReplayService"]
