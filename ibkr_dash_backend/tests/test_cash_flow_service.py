"""Tests for the cash flow service."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.database import Database, init_database
from app.services.cash_flow_service import CashFlowService


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
def cash_flow_service(db: Database) -> CashFlowService:
    """Return a CashFlowService with seeded data."""
    db.insert("cash_flows", {
        "account_id": "U1234567",
        "currency": "USD",
        "date_time": "2026-04-15T12:00:00",
        "settle_date": "2026-04-15",
        "amount": 10000.0,
        "amount_in_base": 10000.0,
        "flow_type": "Deposits/Withdrawals",
        "flow_direction": "deposit",
        "transaction_id": "CF1",
    })
    db.insert("cash_flows", {
        "account_id": "U1234567",
        "currency": "USD",
        "date_time": "2026-04-18T12:00:00",
        "settle_date": "2026-04-18",
        "amount": 5000.0,
        "amount_in_base": 5000.0,
        "flow_type": "Deposits/Withdrawals",
        "flow_direction": "deposit",
        "transaction_id": "CF2",
    })
    db.insert("cash_flows", {
        "account_id": "U1234567",
        "currency": "USD",
        "date_time": "2026-04-18T16:00:00",
        "settle_date": "2026-04-18",
        "amount": 12.5,
        "amount_in_base": 12.5,
        "flow_type": "Ordinary Dividend",
        "symbol": "AAPL",
        "transaction_id": "CF3",
    })
    return CashFlowService(db)


def test_list_cash_flows_returns_deposit_withdrawals_only(
    cash_flow_service: CashFlowService,
) -> None:
    """Test that list_cash_flows returns only deposits/withdrawals by default."""
    result = cash_flow_service.list_cash_flows(
        start_date=None, end_date=None, currency=None,
        flow_direction=None, sort_by="date_time", sort_order="desc",
        page=1, page_size=10,
    )
    assert len(result.items) == 2
    assert all(item.flow_type == "Deposits/Withdrawals" for item in result.items)


def test_list_cash_flows_filters_by_date(cash_flow_service: CashFlowService) -> None:
    """Test that list_cash_flows filters by date range."""
    result = cash_flow_service.list_cash_flows(
        start_date="2026-04-18", end_date=None, currency=None,
        flow_direction=None, sort_by="date_time", sort_order="desc",
        page=1, page_size=10,
    )
    assert len(result.items) == 1
    assert result.items[0].amount == 5000.0


def test_list_cash_flows_pagination(cash_flow_service: CashFlowService) -> None:
    """Test that list_cash_flows paginates correctly."""
    result = cash_flow_service.list_cash_flows(
        start_date=None, end_date=None, currency=None,
        flow_direction=None, sort_by="date_time", sort_order="asc",
        page=1, page_size=1,
    )
    assert len(result.items) == 1
    assert result.pagination.total == 2
    assert result.pagination.total_pages == 2


def test_list_cash_flows_empty_when_no_data(db: Database) -> None:
    """Test that list_cash_flows returns empty when no data."""
    service = CashFlowService(db)
    result = service.list_cash_flows(
        start_date=None, end_date=None, currency=None,
        flow_direction=None, sort_by="date_time", sort_order="desc",
        page=1, page_size=10,
    )
    assert len(result.items) == 0
    assert result.pagination.total == 0
