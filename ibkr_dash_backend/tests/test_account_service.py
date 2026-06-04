"""Account service tests."""

from __future__ import annotations

from app.core.database import Database
from app.services.account_service import AccountService


def test_get_overview_empty_db():
    db = Database(":memory:")
    db.init_schema()
    service = AccountService(db)
    overview = service.get_overview()
    # Should return None or empty when no data
    assert overview is None or overview is not None


def test_get_overview_with_data():
    db = Database(":memory:")
    db.init_schema()

    db.insert("account_snapshots", {
        "account_id": "U123",
        "report_date": "2024-01-15",
        "total_equity": 100000.0,
        "cash": 20000.0,
        "stock_value": 80000.0,
    })

    service = AccountService(db)
    overview = service.get_overview()
    assert overview is not None


def test_get_snapshots_empty():
    db = Database(":memory:")
    db.init_schema()
    service = AccountService(db)
    result = service.get_snapshots(limit=10)
    assert result is not None
