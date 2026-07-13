"""Tests for PortfolioDailyLoopRepository with SQLite."""

from __future__ import annotations

import uuid

from app.domains.portfolio_manager.daily_loop.repository import PortfolioDailyLoopRepository
from tests.pm_helpers import make_test_db


def make_repo() -> PortfolioDailyLoopRepository:
    return PortfolioDailyLoopRepository(make_test_db())


def test_create_and_get_run() -> None:
    repo = make_repo()
    run_id = str(uuid.uuid4())
    doc = {"id": run_id, "run_date": "2026-07-13", "run_type": "manual", "status": "completed"}
    created = repo.create_run(doc)
    assert created["id"] == run_id
    fetched = repo.get_run(run_id)
    assert fetched is not None
    assert fetched["run_date"] == "2026-07-13"


def test_update_run() -> None:
    repo = make_repo()
    run_id = str(uuid.uuid4())
    repo.create_run({"id": run_id, "status": "running"})
    updated = repo.update_run(run_id, {"status": "completed"})
    assert updated is not None
    assert updated["status"] == "completed"


def test_list_runs_with_date_filter() -> None:
    repo = make_repo()
    repo.create_run({"id": str(uuid.uuid4()), "run_date": "2026-07-13", "status": "completed"})
    repo.create_run({"id": str(uuid.uuid4()), "run_date": "2026-07-12", "status": "completed"})
    runs = repo.list_runs(run_date="2026-07-13")
    assert len(runs) == 1


def test_get_latest_run() -> None:
    repo = make_repo()
    assert repo.get_latest_run() is None
    repo.create_run({"id": str(uuid.uuid4()), "run_date": "2026-07-13", "status": "completed"})
    latest = repo.get_latest_run()
    assert latest is not None
