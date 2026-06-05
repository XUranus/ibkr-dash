"""Tests for the agent task service."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.database import Database, init_database
from app.services.agent_services import AgentTaskService, VALID_STATUSES, TERMINAL_STATUSES


@pytest.fixture
def settings() -> Settings:
    """Return test settings with in-memory SQLite."""
    return Settings(
        sqlite_path=":memory:",
        debug=True,
        auth_password="",
    )


@pytest.fixture
def db(settings: Settings) -> Database:
    """Return an initialized in-memory database."""
    return init_database(settings)


@pytest.fixture
def task_service(db: Database) -> AgentTaskService:
    """Return an AgentTaskService instance."""
    return AgentTaskService(db)


def test_create_task(task_service: AgentTaskService) -> None:
    """Test that create_task creates a task in pending status."""
    task = task_service.create_task("daily_position_review")
    assert task["agent_name"] == "daily_position_review"
    assert task["status"] == "pending"
    assert task["id"] is not None
    assert task["created_at"] is not None


def test_get_task(task_service: AgentTaskService) -> None:
    """Test that get_task retrieves a task by ID."""
    created = task_service.create_task("test_agent")
    retrieved = task_service.get_task(created["id"])
    assert retrieved is not None
    assert retrieved["id"] == created["id"]
    assert retrieved["agent_name"] == "test_agent"


def test_get_task_returns_none_for_missing(task_service: AgentTaskService) -> None:
    """Test that get_task returns None for non-existent IDs."""
    result = task_service.get_task("non-existent-id")
    assert result is None


def test_list_tasks(task_service: AgentTaskService) -> None:
    """Test that list_tasks returns tasks."""
    task_service.create_task("agent_a")
    task_service.create_task("agent_b")
    task_service.create_task("agent_a")

    all_tasks = task_service.list_tasks()
    assert len(all_tasks) == 3

    filtered = task_service.list_tasks(agent_name="agent_a")
    assert len(filtered) == 2
    assert all(t["agent_name"] == "agent_a" for t in filtered)


def test_list_tasks_filters_by_status(task_service: AgentTaskService) -> None:
    """Test that list_tasks filters by status."""
    task1 = task_service.create_task("agent_a")
    task_service.create_task("agent_a")
    task_service.start_task(task1["id"])

    pending = task_service.list_tasks(status="pending")
    running = task_service.list_tasks(status="running")
    assert len(pending) == 1
    assert len(running) == 1


def test_list_tasks_pagination(task_service: AgentTaskService) -> None:
    """Test that list_tasks paginates correctly."""
    for _ in range(5):
        task_service.create_task("agent")

    page1 = task_service.list_tasks(limit=2, offset=0)
    page2 = task_service.list_tasks(limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert page1[0]["id"] != page2[0]["id"]


def test_start_task_transitions_to_running(task_service: AgentTaskService) -> None:
    """Test that start_task transitions from pending to running."""
    task = task_service.create_task("test_agent")
    updated = task_service.start_task(task["id"])
    assert updated is not None
    assert updated["status"] == "running"
    assert updated["started_at"] is not None


def test_start_task_raises_if_not_pending(task_service: AgentTaskService) -> None:
    """Test that start_task raises ValueError if task is not pending."""
    task = task_service.create_task("test_agent")
    task_service.start_task(task["id"])

    with pytest.raises(ValueError, match="current status is 'running'"):
        task_service.start_task(task["id"])


def test_start_task_returns_none_for_missing(task_service: AgentTaskService) -> None:
    """Test that start_task returns None for non-existent task."""
    result = task_service.start_task("non-existent")
    assert result is None


def test_complete_task(task_service: AgentTaskService) -> None:
    """Test that complete_task transitions from running to completed."""
    task = task_service.create_task("test_agent")
    task_service.start_task(task["id"])

    result_data = {"summary": "All good"}
    updated = task_service.complete_task(task["id"], result=result_data)
    assert updated is not None
    assert updated["status"] == "completed"
    assert updated["finished_at"] is not None
    assert updated["result"] == result_data


def test_complete_task_raises_if_not_running(task_service: AgentTaskService) -> None:
    """Test that complete_task raises ValueError if task is not running."""
    task = task_service.create_task("test_agent")

    with pytest.raises(ValueError, match="current status is 'pending'"):
        task_service.complete_task(task["id"])


def test_fail_task(task_service: AgentTaskService) -> None:
    """Test that fail_task transitions from running to failed."""
    task = task_service.create_task("test_agent")
    task_service.start_task(task["id"])

    updated = task_service.fail_task(task["id"], error="Something went wrong")
    assert updated is not None
    assert updated["status"] == "failed"
    assert updated["error"] == "Something went wrong"
    assert updated["finished_at"] is not None


def test_fail_task_raises_if_not_running(task_service: AgentTaskService) -> None:
    """Test that fail_task raises ValueError if task is not running."""
    task = task_service.create_task("test_agent")

    with pytest.raises(ValueError, match="current status is 'pending'"):
        task_service.fail_task(task["id"], error="err")


def test_cancel_task_from_pending(task_service: AgentTaskService) -> None:
    """Test that cancel_task works for pending tasks."""
    task = task_service.create_task("test_agent")
    updated = task_service.cancel_task(task["id"])
    assert updated is not None
    assert updated["status"] == "cancelled"
    assert updated["finished_at"] is not None


def test_cancel_task_from_running(task_service: AgentTaskService) -> None:
    """Test that cancel_task works for running tasks."""
    task = task_service.create_task("test_agent")
    task_service.start_task(task["id"])

    updated = task_service.cancel_task(task["id"])
    assert updated is not None
    assert updated["status"] == "cancelled"


def test_cancel_task_raises_if_terminal(task_service: AgentTaskService) -> None:
    """Test that cancel_task raises ValueError for completed tasks."""
    task = task_service.create_task("test_agent")
    task_service.start_task(task["id"])
    task_service.complete_task(task["id"])

    with pytest.raises(ValueError, match="terminal"):
        task_service.cancel_task(task["id"])


def test_cancel_task_returns_none_for_missing(task_service: AgentTaskService) -> None:
    """Test that cancel_task returns None for non-existent task."""
    result = task_service.cancel_task("non-existent")
    assert result is None


def test_update_progress(task_service: AgentTaskService) -> None:
    """Test that update_progress stores progress data."""
    task = task_service.create_task("test_agent")

    updated = task_service.update_progress(task["id"], {"step": 1, "total": 5})
    assert updated is not None
    assert updated["progress"] == {"step": 1, "total": 5}


def test_full_task_lifecycle(task_service: AgentTaskService) -> None:
    """Test the full lifecycle: create -> start -> progress -> complete."""
    task = task_service.create_task("daily_position_review")
    assert task["status"] == "pending"

    task = task_service.start_task(task["id"])
    assert task["status"] == "running"

    task = task_service.update_progress(task["id"], {"positions_analyzed": 10})
    assert task["progress"]["positions_analyzed"] == 10

    task = task_service.complete_task(task["id"], result={"review": "positive"})
    assert task["status"] == "completed"
    assert task["result"]["review"] == "positive"


def test_valid_statuses_constant() -> None:
    """Test that VALID_STATUSES contains expected values."""
    assert "pending" in VALID_STATUSES
    assert "running" in VALID_STATUSES
    assert "completed" in VALID_STATUSES
    assert "failed" in VALID_STATUSES
    assert "cancelled" in VALID_STATUSES


def test_terminal_statuses_constant() -> None:
    """Test that TERMINAL_STATUSES contains expected values."""
    assert "completed" in TERMINAL_STATUSES
    assert "failed" in TERMINAL_STATUSES
    assert "cancelled" in TERMINAL_STATUSES
    assert "pending" not in TERMINAL_STATUSES
    assert "running" not in TERMINAL_STATUSES
