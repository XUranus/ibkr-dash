"""Agent task management service.

Runs agents in background threads, tracks task status,
and stores results in the agent_tasks table.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import uuid
from typing import Any, Callable

from app.core.database import Database
from app.utils.dates import utc_now_iso

logger = logging.getLogger(__name__)

VALID_STATUSES = {"pending", "running", "completed", "failed", "cancelled"}
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


class AgentTaskService:
    """Manages background agent tasks with status tracking."""

    def __init__(self, db: Database) -> None:
        self.db = db
        self._running_tasks: dict[str, threading.Thread] = {}

    def create_task(self, agent_name: str) -> dict:
        """Create a new agent task and return the task dict."""
        task_id = str(uuid.uuid4())
        now = utc_now_iso()
        self.db.insert("agent_tasks", {
            "id": task_id,
            "agent_name": agent_name,
            "status": "pending",
            "progress": json.dumps({"step": "queued"}),
            "created_at": now,
        })
        return {
            "id": task_id,
            "agent_name": agent_name,
            "status": "pending",
            "progress": {"step": "queued"},
            "created_at": now,
        }

    def update_task_status(
        self,
        task_id: str,
        status: str,
        *,
        progress: dict | None = None,
        result: dict | None = None,
        error: str | None = None,
    ) -> None:
        """Update task status in the database."""
        data: dict[str, Any] = {"status": status}
        if progress is not None:
            data["progress"] = json.dumps(progress, ensure_ascii=False, default=str)
        if result is not None:
            data["result"] = json.dumps(result, ensure_ascii=False, default=str)
        if error is not None:
            data["error"] = error[:2000]
        if status == "running":
            data["started_at"] = utc_now_iso()
        elif status in ("completed", "failed", "cancelled"):
            data["finished_at"] = utc_now_iso()

        # UPDATE existing task (task must already exist)
        set_clause = ", ".join(f"{k} = ?" for k in data.keys())
        sql = f"UPDATE agent_tasks SET {set_clause} WHERE id = ?"
        self.db.execute(sql, (*data.values(), task_id))

    def get_task(self, task_id: str) -> dict | None:
        """Get task by ID."""
        row = self.db.execute_one("SELECT * FROM agent_tasks WHERE id = ?", (task_id,))
        if row and isinstance(row.get("result"), str):
            try:
                row["result"] = json.loads(row["result"])
            except (json.JSONDecodeError, TypeError):
                pass
        if row and isinstance(row.get("progress"), str):
            try:
                row["progress"] = json.loads(row["progress"])
            except (json.JSONDecodeError, TypeError):
                pass
        return row

    def list_tasks(
        self,
        agent_name: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """List tasks with optional filters and pagination."""
        conditions = []
        params: list[Any] = []
        if agent_name:
            conditions.append("agent_name = ?")
            params.append(agent_name)
        if status:
            conditions.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM agent_tasks {where} ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return self.db.execute(sql, tuple(params))

    def run_in_background(
        self,
        agent_name: str,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """Run an async agent function in a background thread.

        Args:
            agent_name: Name of the agent for tracking.
            func: Async function to execute.
            *args, **kwargs: Arguments to pass to func.

        Returns:
            Task ID for status tracking.
        """
        task_id = self.create_task(agent_name)

        def _worker() -> None:
            self.update_task_status(task_id, "running")
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(func(*args, **kwargs))
                    self.update_task_status(task_id, "completed", result=result)
                finally:
                    loop.close()
            except Exception as exc:
                logger.exception("Agent task %s failed: %s", task_id, exc)
                self.update_task_status(task_id, "failed", error=str(exc))
            finally:
                self._running_tasks.pop(task_id, None)

        thread = threading.Thread(target=_worker, name=f"agent-{agent_name}-{task_id[:8]}", daemon=True)
        self._running_tasks[task_id] = thread
        thread.start()
        return task_id

    def start_task(self, task_id: str) -> dict | None:
        """Transition a task from pending to running.

        Returns:
            The updated task dict, or None if task not found.

        Raises:
            ValueError: If the task is not in pending status.
        """
        task = self.get_task(task_id)
        if task is None:
            return None
        if task["status"] != "pending":
            raise ValueError(
                f"Cannot start task {task_id}: current status is '{task['status']}', expected 'pending'"
            )
        self.update_task_status(task_id, "running")
        return self.get_task(task_id)

    def complete_task(self, task_id: str, result: dict | None = None) -> dict | None:
        """Transition a task to completed status.

        Args:
            task_id: The task ID.
            result: Optional result data to store.

        Returns:
            The updated task dict, or None if task not found.

        Raises:
            ValueError: If the task is not in running status.
        """
        task = self.get_task(task_id)
        if task is None:
            return None
        if task["status"] != "running":
            raise ValueError(
                f"Cannot complete task {task_id}: current status is '{task['status']}', expected 'running'"
            )
        self.update_task_status(task_id, "completed", result=result)
        return self.get_task(task_id)

    def fail_task(self, task_id: str, error: str) -> dict | None:
        """Transition a task to failed status.

        Args:
            task_id: The task ID.
            error: Error message to store.

        Returns:
            The updated task dict, or None if task not found.

        Raises:
            ValueError: If the task is not in running status.
        """
        task = self.get_task(task_id)
        if task is None:
            return None
        if task["status"] != "running":
            raise ValueError(
                f"Cannot fail task {task_id}: current status is '{task['status']}', expected 'running'"
            )
        self.update_task_status(task_id, "failed", error=error)
        return self.get_task(task_id)

    def update_progress(self, task_id: str, progress: dict) -> dict | None:
        """Update the progress field of a running task.

        Args:
            task_id: The task ID.
            progress: Progress data to store.

        Returns:
            The updated task dict, or None if task not found.
        """
        task = self.get_task(task_id)
        if task is None:
            return None
        self.update_task_status(task_id, task.get("status", "running"), progress=progress)
        return self.get_task(task_id)

    def cancel_task(self, task_id: str) -> dict | None:
        """Cancel a pending or running task.

        Returns:
            The updated task dict, or None if task not found.

        Raises:
            ValueError: If the task is already in a terminal status.
        """
        task = self.get_task(task_id)
        if task is None:
            return None
        if task["status"] in TERMINAL_STATUSES:
            raise ValueError(
                f"Cannot cancel task {task_id}: current status is '{task['status']}' (terminal)"
            )
        self.update_task_status(task_id, "cancelled")
        return self.get_task(task_id)

    def get_running_task_ids(self) -> list[str]:
        """Return IDs of currently running tasks."""
        return list(self._running_tasks.keys())
