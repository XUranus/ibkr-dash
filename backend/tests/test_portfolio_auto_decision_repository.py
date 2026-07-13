"""Tests for PortfolioAutoDecisionRepository with SQLite."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.domains.portfolio_manager.decision_orchestrator.repository import PortfolioAutoDecisionRepository
from tests.pm_helpers import make_test_db


def make_repo() -> PortfolioAutoDecisionRepository:
    return PortfolioAutoDecisionRepository(make_test_db())


def test_create_and_get_run() -> None:
    repo = make_repo()
    run_id = str(uuid.uuid4())
    doc = {"id": run_id, "run_date": "2026-07-13", "run_type": "manual", "status": "completed"}
    created = repo.create_run(doc)
    assert created["id"] == run_id
    fetched = repo.get_run(run_id)
    assert fetched is not None


def test_update_run() -> None:
    repo = make_repo()
    run_id = str(uuid.uuid4())
    repo.create_run({"id": run_id, "status": "running"})
    updated = repo.update_run(run_id, {"status": "completed"})
    assert updated is not None
    assert updated["status"] == "completed"


def test_bulk_create_items() -> None:
    repo = make_repo()
    run_id = str(uuid.uuid4())
    items = [
        {"id": str(uuid.uuid4()), "run_id": run_id, "symbol": "AAPL", "selection_status": "completed"},
        {"id": str(uuid.uuid4()), "run_id": run_id, "symbol": "TSLA", "selection_status": "skipped"},
    ]
    created = repo.bulk_create_items(items)
    assert len(created) == 2
    listed = repo.list_items(run_id)
    assert len(listed) == 2


def test_update_item() -> None:
    repo = make_repo()
    item_id = str(uuid.uuid4())
    repo.bulk_create_items([{"id": item_id, "run_id": "r1", "symbol": "AAPL", "selection_status": "pending"}])
    updated = repo.update_item(item_id, {"selection_status": "completed"})
    assert updated is not None
    assert updated["selection_status"] == "completed"


def test_find_recent_completed() -> None:
    repo = make_repo()
    item_id = str(uuid.uuid4())
    repo.bulk_create_items([{"id": item_id, "run_id": "r1", "symbol": "AAPL", "selection_status": "completed"}])
    result = repo.find_recent_completed("AAPL", datetime(2020, 1, 1, tzinfo=timezone.utc))
    assert result is not None


def test_list_symbol_history() -> None:
    repo = make_repo()
    repo.bulk_create_items([
        {"id": str(uuid.uuid4()), "run_id": "r1", "symbol": "AAPL", "selection_status": "completed"},
        {"id": str(uuid.uuid4()), "run_id": "r2", "symbol": "AAPL", "selection_status": "completed"},
    ])
    history = repo.list_symbol_history("AAPL")
    assert len(history) == 2
