"""Agent task service: CRUD and status management for agent tasks.

Manages the lifecycle of AI agent tasks stored in the agent_tasks table.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from app.core.database import Database

VALID_STATUSES = {"pending", "running", "completed", "failed", "cancelled"}
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


class AgentTaskService:
    """Service for managing agent task lifecycle."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def create_task(self, agent_name: str) -> dict:
        """Create a new agent task in pending status.

        Args:
            agent_name: The name of the agent (e.g., 'daily_position_review').

        Returns:
            The created task as a dict.
        """
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        self.db.insert("agent_tasks", {
            "id": task_id,
            "agent_name": agent_name,
            "status": "pending",
            "created_at": now,
        })
        return self.get_task(task_id)

    def get_task(self, task_id: str) -> dict | None:
        """Retrieve a task by ID.

        Returns:
            The task dict, or None if not found.
        """
        row = self.db.execute_one(
            "SELECT * FROM agent_tasks WHERE id = ?", (task_id,)
        )
        if row is None:
            return None
        return self._deserialize_row(row)

    def list_tasks(
        self,
        agent_name: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List tasks with optional filters.

        Args:
            agent_name: Filter by agent name.
            status: Filter by status.
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            List of task dicts.
        """
        conditions = []
        params: list = []
        if agent_name:
            conditions.append("agent_name = ?")
            params.append(agent_name)
        if status:
            conditions.append("status = ?")
            params.append(status)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.extend([limit, offset])

        rows = self.db.execute(
            f"SELECT * FROM agent_tasks {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            tuple(params),
        )
        return [self._deserialize_row(row) for row in rows]

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
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "UPDATE agent_tasks SET status = 'running', started_at = ? WHERE id = ?",
            (now, task_id),
        )
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
        now = datetime.now(timezone.utc).isoformat()
        result_json = json.dumps(result) if result else None
        self.db.execute(
            "UPDATE agent_tasks SET status = 'completed', finished_at = ?, result = ? WHERE id = ?",
            (now, result_json, task_id),
        )
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
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "UPDATE agent_tasks SET status = 'failed', finished_at = ?, error = ? WHERE id = ?",
            (now, error, task_id),
        )
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
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "UPDATE agent_tasks SET status = 'cancelled', finished_at = ? WHERE id = ?",
            (now, task_id),
        )
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
        progress_json = json.dumps(progress)
        self.db.execute(
            "UPDATE agent_tasks SET progress = ? WHERE id = ?",
            (progress_json, task_id),
        )
        return self.get_task(task_id)

    @staticmethod
    def _deserialize_row(row: dict) -> dict:
        """Deserialize JSON fields in a task row."""
        result = dict(row)
        for field in ("progress", "result"):
            if result.get(field) and isinstance(result[field], str):
                try:
                    result[field] = json.loads(result[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return result
