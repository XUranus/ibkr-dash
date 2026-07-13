"""Tests for PortfolioImprovementRepository with SQLite."""

from __future__ import annotations

import uuid

from app.domains.portfolio_manager.improvement.repository import PortfolioImprovementRepository
from tests.pm_helpers import make_test_db


def make_repo() -> PortfolioImprovementRepository:
    return PortfolioImprovementRepository(make_test_db())


def test_create_and_get_report() -> None:
    repo = make_repo()
    report_id = str(uuid.uuid4())
    doc = {"id": report_id, "report_date": "2026-07-13", "report_type": "weekly", "status": "completed"}
    created = repo.create_report(doc)
    assert created["id"] == report_id
    fetched = repo.get_report(report_id)
    assert fetched is not None
    assert fetched["report_date"] == "2026-07-13"


def test_list_reports_with_date_filter() -> None:
    repo = make_repo()
    repo.create_report({"id": str(uuid.uuid4()), "report_date": "2026-07-13", "status": "completed"})
    repo.create_report({"id": str(uuid.uuid4()), "report_date": "2026-07-12", "status": "completed"})
    reports = repo.list_reports(report_date="2026-07-13")
    assert len(reports) == 1


def test_get_latest_report() -> None:
    repo = make_repo()
    assert repo.get_latest_report() is None
    repo.create_report({"id": str(uuid.uuid4()), "report_date": "2026-07-13", "status": "completed"})
    latest = repo.get_latest_report()
    assert latest is not None
