"""Tests for the dividend service."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.database import Database, init_database
from app.services.dividend_service import DividendService


@pytest.fixture
def settings() -> Settings:
    return Settings()

@pytest.fixture
def db(settings: Settings) -> Database:
    return init_database(settings)





@pytest.fixture
def dividend_service(db: Database) -> DividendService:
    """Return a DividendService with seeded data."""
    db.insert("cash_flows", {
        "account_id": "U1234567",
        "currency": "USD",
        "symbol": "AAPL",
        "date_time": "2026-04-18T16:00:00",
        "settle_date": "2026-04-18",
        "amount": 12.5,
        "flow_type": "Ordinary Dividend",
        "dividend_type": "Ordinary Dividend",
        "transaction_id": "DIV1",
    })
    db.insert("cash_flows", {
        "account_id": "U1234567",
        "currency": "USD",
        "symbol": "MSFT",
        "date_time": "2026-04-18T16:00:00",
        "settle_date": "2026-04-18",
        "amount": 8.0,
        "flow_type": "Ordinary Dividend",
        "dividend_type": "Ordinary Dividend",
        "transaction_id": "DIV2",
    })
    db.insert("cash_flows", {
        "account_id": "U1234567",
        "currency": "USD",
        "symbol": "AAPL",
        "date_time": "2026-04-18T16:00:00",
        "settle_date": "2026-04-18",
        "amount": -1.25,
        "flow_type": "Withholding Tax",
        "transaction_id": "DIV3",
    })
    # Non-dividend flow that should be excluded
    db.insert("cash_flows", {
        "account_id": "U1234567",
        "currency": "USD",
        "date_time": "2026-04-15T12:00:00",
        "settle_date": "2026-04-15",
        "amount": 10000.0,
        "flow_type": "Deposits/Withdrawals",
        "transaction_id": "CF1",
    })
    return DividendService(db)

def test_list_dividends_returns_only_dividend_flows(
    dividend_service: DividendService,
) -> None:
    """Test that list_dividends returns only dividend-related flows."""
    result = dividend_service.list_dividends(
        start_date=None, end_date=None, currency=None, symbol=None,
        sort_by="date_time", sort_order="desc", page=1, page_size=10,)
    assert len(result.items) == 3
    flow_types = {item.flow_type for item in result.items}
    assert "Deposits/Withdrawals" not in flow_types
    assert "Ordinary Dividend" in flow_types
    assert "Withholding Tax" in flow_types

def test_list_dividends_filters_by_symbol(
    dividend_service: DividendService,
) -> None:
    """Test that list_dividends filters by symbol."""
    result = dividend_service.list_dividends(
        start_date=None, end_date=None, currency=None, symbol="AAPL",
        sort_by="date_time", sort_order="desc", page=1, page_size=10,)
    assert len(result.items) == 2
    assert all(item.symbol == "AAPL" for item in result.items)

def test_list_dividends_pagination(dividend_service: DividendService) -> None:
    """Test that list_dividends paginates correctly."""
    result = dividend_service.list_dividends(
        start_date=None, end_date=None, currency=None, symbol=None,
        sort_by="date_time", sort_order="desc", page=1, page_size=2,)
    assert len(result.items) == 2
    assert result.pagination.total == 3
    assert result.pagination.total_pages == 2

def test_list_dividends_empty_when_no_data(db: Database) -> None:
    """Test that list_dividends returns empty when no dividend data."""
    service = DividendService(db)
    result = service.list_dividends(
        start_date=None, end_date=None, currency=None, symbol=None,
        sort_by="date_time", sort_order="desc", page=1, page_size=10,)
    assert len(result.items) == 0
    assert result.pagination.total == 0
