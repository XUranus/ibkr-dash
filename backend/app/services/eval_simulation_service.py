"""Evaluation simulation service -- run agent evaluations against test cases.

Provides a simplified evaluation harness that runs agent tasks against
predefined test cases and records results.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

from app.core.database import Database
from app.utils.dates import utc_now_iso

logger = logging.getLogger(__name__)


class EvalSimulationService:
    """Run and manage agent evaluation simulations."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def list_simulations(self, limit: int = 50, offset: int = 0) -> dict:
        """List evaluation simulations."""
        rows = self.db.execute(
            "SELECT * FROM agent_replays ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        total = self.db.execute_one("SELECT COUNT(*) as cnt FROM agent_replays")
        return {
            "items": rows,
            "total": total["cnt"] if total else 0,
            "limit": limit,
            "offset": offset,
        }

    def get_simulation(self, replay_id: str) -> dict | None:
        """Get a specific simulation by ID."""
        return self.db.execute_one(
            "SELECT * FROM agent_replays WHERE replay_id = ?",
            (replay_id,),
        )

    def record_simulation(
        self,
        *,
        run_id: str,
        agent_name: str,
        payload: dict,
        status: str = "success",
    ) -> dict:
        """Record a simulation result."""
        replay_id = uuid4().hex[:16]
        self.db.execute(
            """INSERT INTO agent_replays (replay_id, run_id, agent_name, final_status, created_at, payload_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (replay_id, run_id, agent_name, status, utc_now_iso(), json.dumps(payload)),
        )
        return {"replay_id": replay_id, "status": status}

    def get_agent_stats(self, days: int = 30) -> list[dict]:
        """Get per-agent evaluation statistics."""
        return self.db.execute(
            """SELECT
                agent_name,
                COUNT(*) as total_runs,
                SUM(CASE WHEN final_status = 'success' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN final_status = 'failed' THEN 1 ELSE 0 END) as failed_count
            FROM agent_replays
            WHERE created_at >= datetime('now', ?)
            GROUP BY agent_name
            ORDER BY total_runs DESC""",
            (f"-{days} days",),
        )


# --- Compatibility alias ---
SyntheticSimulationService = EvalSimulationService
