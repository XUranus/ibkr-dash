"""Copilot chat API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.database import Database, init_database
from app.main import app


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    """Use in-memory DB for tests."""
    import app.core.database as db_mod
    from app.core.config import get_settings

    # Clear cached singletons so the monkeypatched env takes effect
    db_mod._db_instance = None
    get_settings.cache_clear()
    monkeypatch.setenv("SQLITE_PATH", ":memory:")

    # Create a fresh in-memory database with schema initialized
    db_mod.init_database()

    yield

    db_mod._db_instance = None
    get_settings.cache_clear()


client = TestClient(app)


def test_list_sessions_empty():
    response = client.get("/api/copilot/sessions")
    assert response.status_code == 200
    assert response.json() == []


def test_chat_creates_session():
    # This will fail because LLM is not configured, but it should create a session
    response = client.post("/api/copilot/chat", json={"message": "Hello"})
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "run_id" in data
    assert "answer" in data


def test_chat_with_nonexistent_session():
    response = client.post("/api/copilot/chat", json={
        "session_id": "nonexistent",
        "message": "Hello",
    })
    assert response.status_code == 404


def test_delete_nonexistent_session():
    response = client.delete("/api/copilot/sessions/nonexistent")
    assert response.status_code == 404


def test_chat_and_list_messages():
    # Create a session via chat
    response = client.post("/api/copilot/chat", json={"message": "Test message"})
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    # List messages
    msg_response = client.get(f"/api/copilot/sessions/{session_id}/messages")
    assert msg_response.status_code == 200
    messages = msg_response.json()
    assert len(messages) >= 2  # user + assistant
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Test message"


def test_delete_session():
    # Create a session
    response = client.post("/api/copilot/chat", json={"message": "To delete"})
    session_id = response.json()["session_id"]

    # Delete it
    del_response = client.delete(f"/api/copilot/sessions/{session_id}")
    assert del_response.status_code == 204

    # Verify it's gone
    msg_response = client.get(f"/api/copilot/sessions/{session_id}/messages")
    assert msg_response.status_code == 200
    assert msg_response.json() == []
