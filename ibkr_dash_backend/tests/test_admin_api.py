"""Admin API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
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


def test_system_status():
    response = client.get("/api/admin/system/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "llm" in data
    assert "runtime" in data


def test_list_prompts_empty():
    response = client.get("/api/admin/prompts")
    assert response.status_code == 200
    assert response.json() == []


def test_create_prompt():
    response = client.post("/api/admin/prompts", json={
        "prompt_key": "test_prompt",
        "content": "You are a test assistant.",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["prompt_key"] == "test_prompt"
    assert data["version"] == 1
    assert data["status"] == "active"


def test_create_prompt_versioning():
    client.post("/api/admin/prompts", json={
        "prompt_key": "versioned",
        "content": "Version 1",
    })
    response = client.post("/api/admin/prompts", json={
        "prompt_key": "versioned",
        "content": "Version 2",
    })
    assert response.status_code == 200
    assert response.json()["version"] == 2


def test_get_active_prompt():
    client.post("/api/admin/prompts", json={
        "prompt_key": "active_test",
        "content": "Active content",
    })
    response = client.get("/api/admin/prompts/active_test/active")
    assert response.status_code == 200
    assert response.json()["content"] == "Active content"


def test_get_active_prompt_not_found():
    response = client.get("/api/admin/prompts/nonexistent/active")
    assert response.status_code == 404
