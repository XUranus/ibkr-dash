"""LLM call metrics service -- track LLM API usage and costs."""

from __future__ import annotations

import logging
from uuid import uuid4

from app.core.database import Database
from app.utils.dates import utc_now_iso

logger = logging.getLogger(__name__)


class LLMCallMetricsService:
    """Track and query LLM call metrics."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def record_call(
        self,
        *,
        agent_name: str | None = None,
        model: str | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: int = 0,
        status: str = "success",
        error: str | None = None,
    ) -> dict:
        """Record a single LLM call."""
        call_id = uuid4().hex[:16]
        total = prompt_tokens + completion_tokens
        self.db.execute(
            """INSERT INTO llm_call_metrics
               (call_id, agent_name, model, prompt_tokens, completion_tokens, total_tokens, latency_ms, status, error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (call_id, agent_name, model, prompt_tokens, completion_tokens, total, latency_ms, status, error),
        )
        return {
            "call_id": call_id,
            "agent_name": agent_name,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total,
            "latency_ms": latency_ms,
            "status": status,
        }

    def list_calls(
        self,
        *,
        agent_name: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """List LLM call metrics with optional filtering."""
        conditions = []
        params: list = []
        if agent_name:
            conditions.append("agent_name = ?")
            params.append(agent_name)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = self.db.execute(
            f"SELECT * FROM llm_call_metrics {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )
        total = self.db.execute_one(
            f"SELECT COUNT(*) as cnt FROM llm_call_metrics {where}",
            tuple(params),
        )
        return {
            "items": rows,
            "total": total["cnt"] if total else 0,
            "limit": limit,
            "offset": offset,
        }

    def get_stats(self, days: int = 30) -> dict:
        """Get aggregated LLM call statistics."""
        rows = self.db.execute(
            """SELECT
                COUNT(*) as total_calls,
                SUM(prompt_tokens) as total_prompt_tokens,
                SUM(completion_tokens) as total_completion_tokens,
                SUM(total_tokens) as total_tokens,
                AVG(latency_ms) as avg_latency_ms,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
            FROM llm_call_metrics
            WHERE created_at >= datetime('now', ?)""",
            (f"-{days} days",),
        )
        if rows:
            return rows[0]
        return {
            "total_calls": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "avg_latency_ms": 0,
            "error_count": 0,
        }

    def get_agent_breakdown(self, days: int = 30) -> list[dict]:
        """Get per-agent LLM call breakdown."""
        return self.db.execute(
            """SELECT
                agent_name,
                COUNT(*) as calls,
                SUM(total_tokens) as tokens,
                AVG(latency_ms) as avg_latency_ms
            FROM llm_call_metrics
            WHERE created_at >= datetime('now', ?)
            GROUP BY agent_name
            ORDER BY tokens DESC""",
            (f"-{days} days",),
        )
