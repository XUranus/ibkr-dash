"""Admin agent monitoring endpoints."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)

from app.api.deps import get_current_user, get_db
from app.core.database import Database

router = APIRouter(prefix="/admin/agent-monitoring", tags=["admin", "monitoring"])


@router.get("/overview")
def monitoring_overview(
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    """Return agent monitoring overview: recent events, tool metrics, LLM metrics."""
    tasks = db.execute(
        "SELECT id, agent_name, status, error, progress, created_at, started_at, finished_at "
        "FROM agent_tasks ORDER BY created_at DESC LIMIT 20"
    )
    recent_events = []
    for task in tasks:
        level = "error" if task["status"] == "failed" else "info"
        recent_events.append({
            "id": str(task["id"]),
            "timestamp": task["created_at"] or "",
            "level": level,
            "source": task["agent_name"] or "unknown",
            "message": task["error"] or f"Task {task['status']}",
            "details": None,
        })

    # Aggregate metrics from agent_tasks progress
    tool_calls: dict[str, dict] = {}
    # LLM metrics keyed by model
    llm_by_model: dict[str, dict] = {}

    for task in tasks:
        if not task.get("progress"):
            continue
        try:
            progress = json.loads(task["progress"]) if isinstance(task["progress"], str) else task["progress"]

            # Tool metrics
            for tool in progress.get("tools_called", []):
                name = tool.get("name", "unknown") if isinstance(tool, dict) else str(tool)
                if name not in tool_calls:
                    tool_calls[name] = {"tool": name, "calls": 0, "successes": 0, "failures": 0, "total_latency": 0}
                tool_calls[name]["calls"] += tool.get("calls", 1) if isinstance(tool, dict) else 1
                tool_calls[name]["successes"] += tool.get("successes", 0) if isinstance(tool, dict) else (1 if task["status"] == "completed" else 0)
                tool_calls[name]["failures"] += tool.get("failures", 0) if isinstance(tool, dict) else (0 if task["status"] == "completed" else 1)
                tool_calls[name]["total_latency"] += tool.get("total_latency", 0) if isinstance(tool, dict) else 0

            # LLM metrics
            llm_info = progress.get("llm_calls", {})
            if isinstance(llm_info, dict) and llm_info.get("calls"):
                model = llm_info.get("model", "") or "unknown"
                if model not in llm_by_model:
                    llm_by_model[model] = {
                        "model": model, "calls": 0, "totalTokens": 0,
                        "promptTokens": 0, "completionTokens": 0,
                        "totalLatencyMs": 0, "errors": 0,
                    }
                llm_by_model[model]["calls"] += llm_info["calls"]
                llm_by_model[model]["totalTokens"] += llm_info.get("total_tokens", 0)
                llm_by_model[model]["promptTokens"] += llm_info.get("prompt_tokens", 0)
                llm_by_model[model]["completionTokens"] += llm_info.get("completion_tokens", 0)
                llm_by_model[model]["totalLatencyMs"] += llm_info.get("total_latency_ms", 0)
        except (json.JSONDecodeError, TypeError, AttributeError):
            logger.debug("Failed to parse progress for task %s", task.get("id"), exc_info=True)

    tool_metrics = [
        {
            "tool": m["tool"],
            "calls": m["calls"],
            "successes": m["successes"],
            "failures": m["failures"],
            "avgLatencyMs": m["total_latency"] // m["calls"] if m["calls"] else 0,
        }
        for m in tool_calls.values()
    ]

    llm_metrics = [
        {
            "model": m["model"],
            "calls": m["calls"],
            "totalTokens": m["totalTokens"],
            "promptTokens": m["promptTokens"],
            "completionTokens": m["completionTokens"],
            "avgLatencyMs": m["totalLatencyMs"] // m["calls"] if m["calls"] else 0,
            "errors": m["errors"],
        }
        for m in llm_by_model.values()
    ]

    return {
        "recent_events": recent_events,
        "tool_metrics": tool_metrics,
        "llm_metrics": llm_metrics,
    }
