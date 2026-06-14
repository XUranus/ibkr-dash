"""Agent task management API tests."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.core.database import init_database
from app.main import app


@pytest.fixture(autouse=True)
def setup_db():
    """Ensure DB is initialized for each test (conftest handles singleton resets)."""
    init_database()
    yield


client = TestClient(app)


def test_list_tasks_empty():
    response = client.get("/api/agent/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_get_task_not_found():
    response = client.get("/api/agent/tasks/nonexistent-id")
    assert response.status_code == 404


def test_run_agent_unknown():
    response = client.post("/api/agent/run", json={"agent_name": "unknown_agent"})
    assert response.status_code == 400
    assert "Unknown agent" in response.json()["detail"]


def test_run_trade_decision_requires_symbol():
    response = client.post("/api/agent/run", json={"agent_name": "trade_decision"})
    assert response.status_code == 400
    assert "symbol is required" in response.json()["detail"]


def test_run_trade_review_requires_symbol():
    response = client.post("/api/agent/run", json={"agent_name": "trade_review"})
    assert response.status_code == 400
    assert "symbol is required" in response.json()["detail"]
