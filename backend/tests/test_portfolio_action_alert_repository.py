"""Tests for PortfolioActionAlertRepository with SQLite."""

from __future__ import annotations

import uuid

from app.domains.portfolio_manager.action_alerts.repository import PortfolioActionAlertRepository
from tests.pm_helpers import make_test_db


def make_repo() -> PortfolioActionAlertRepository:
    return PortfolioActionAlertRepository(make_test_db())


def test_create_and_get_alert() -> None:
    repo = make_repo()
    alert_id = str(uuid.uuid4())
    doc = {"id": alert_id, "run_date": "2026-07-13", "symbol": "AAPL", "alert_type": "decision_required", "status": "pending"}
    created = repo.create_alert(doc)
    assert created["id"] == alert_id
    fetched = repo.get_alert(alert_id)
    assert fetched is not None
    assert fetched["symbol"] == "AAPL"


def test_upsert_alert() -> None:
    repo = make_repo()
    alert_id = str(uuid.uuid4())
    repo.create_alert({"id": alert_id, "run_date": "2026-07-13", "symbol": "AAPL", "status": "pending"})
    upserted = repo.upsert_alert({"id": alert_id, "run_date": "2026-07-13", "symbol": "AAPL", "status": "sent"})
    assert upserted["status"] == "sent"


def test_list_alerts_with_filters() -> None:
    repo = make_repo()
    repo.create_alert({"id": str(uuid.uuid4()), "run_date": "2026-07-13", "symbol": "AAPL", "status": "pending"})
    repo.create_alert({"id": str(uuid.uuid4()), "run_date": "2026-07-13", "symbol": "TSLA", "status": "sent"})
    pending = repo.list_alerts(status="pending")
    assert len(pending) == 1
    assert pending[0]["symbol"] == "AAPL"


def test_mark_sent() -> None:
    repo = make_repo()
    alert_id = str(uuid.uuid4())
    repo.create_alert({"id": alert_id, "run_date": "2026-07-13", "symbol": "AAPL", "status": "pending"})
    marked = repo.mark_sent(alert_id, email_subject="Test", sent_at="2026-07-13T10:00:00Z")
    assert marked is not None
    assert marked["status"] == "sent"
    assert marked["email_subject"] == "Test"


def test_mark_failed() -> None:
    repo = make_repo()
    alert_id = str(uuid.uuid4())
    repo.create_alert({"id": alert_id, "run_date": "2026-07-13", "symbol": "AAPL", "status": "pending"})
    marked = repo.mark_failed(alert_id, "SMTP error")
    assert marked is not None
    assert marked["status"] == "failed"
    assert marked["email_error"] == "SMTP error"


def test_find_existing_alert() -> None:
    repo = make_repo()
    alert_id = str(uuid.uuid4())
    repo.create_alert({
        "id": alert_id,
        "run_date": "2026-07-13",
        "symbol": "AAPL",
        "alert_type": "decision_required",
        "status": "pending",
        "linked_ids": {"decision_id": "dec-123"},
    })
    found = repo.find_existing_alert(run_date="2026-07-13", symbol="AAPL", alert_type="decision_required", decision_id="dec-123")
    assert found is not None
    assert found["id"] == alert_id
