"""Tests for the trade service."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.database import Database, init_database
from app.services.trade_service import TradeService


@pytest.fixture
def settings() -> Settings:
    return Settings()

@pytest.fixture
def db(settings: Settings) -> Database:
    return init_database(settings)





@pytest.fixture
def trade_service(db: Database) -> TradeService:
    """Return a TradeService with a seeded database."""
    # Insert test trade records
    db.insert("trade_records", {
        "account_id": "U1234567",
        "symbol": "AAPL",
        "trade_date": "2026-04-18",
        "date_time": "2026-04-18T09:35:00",
        "buy_sell": "BUY",
        "quantity": 10.0,
        "trade_price": 190.0,
        "trade_money": 1900.0,
        "proceeds": -1900.0,
        "ib_commission": 1.2,
        "net_cash": -1901.2,
        "fifo_pnl_realized": None,
        "asset_class": "STK",
        "exchange": "NASDAQ",
        "order_type": "LMT",
    })
    db.insert("trade_records", {
        "account_id": "U1234567",
        "symbol": "MSFT",
        "trade_date": "2026-04-18",
        "date_time": "2026-04-18T10:00:00",
        "buy_sell": "BUY",
        "quantity": 5.0,
        "trade_price": 420.0,
        "trade_money": 2100.0,
        "proceeds": -2100.0,
        "ib_commission": 1.0,
        "net_cash": -2101.0,
        "fifo_pnl_realized": None,
        "asset_class": "STK",
        "exchange": "NASDAQ",
        "order_type": "LMT",
    })
    db.insert("trade_records", {
        "account_id": "U1234567",
        "symbol": "AAPL",
        "trade_date": "2026-04-19",
        "date_time": "2026-04-19T14:00:00",
        "buy_sell": "SELL",
        "quantity": 5.0,
        "trade_price": 195.0,
        "trade_money": 975.0,
        "proceeds": 975.0,
        "ib_commission": 1.0,
        "net_cash": 974.0,
        "fifo_pnl_realized": 25.0,
        "asset_class": "STK",
        "exchange": "NASDAQ",
        "order_type": "LMT",
    })
    return TradeService(db)

def test_list_trades_returns_all_trades(trade_service: TradeService) -> None:
    """Test that list_trades returns all trades without filters."""
    result = trade_service.list_trades(
        start_date=None, end_date=None, symbol=None,
        asset_class=None, buy_sell=None, sort_by="date_time",
        sort_order="desc", page=1, page_size=10,)
    assert len(result.items) == 3
    assert result.pagination.total == 3

def test_list_trades_filters_by_symbol(trade_service: TradeService) -> None:
    """Test that list_trades filters by symbol."""
    result = trade_service.list_trades(
        start_date=None, end_date=None, symbol="AAPL",
        asset_class=None, buy_sell=None, sort_by="date_time",
        sort_order="desc", page=1, page_size=10,)
    assert len(result.items) == 2
    assert all(item.symbol == "AAPL" for item in result.items)

def test_list_trades_filters_by_buy_sell(trade_service: TradeService) -> None:
    """Test that list_trades filters by buy/sell direction."""
    result = trade_service.list_trades(
        start_date=None, end_date=None, symbol=None,
        asset_class=None, buy_sell="SELL", sort_by="date_time",
        sort_order="desc", page=1, page_size=10,)
    assert len(result.items) == 1
    assert result.items[0].buy_sell == "SELL"
    assert result.items[0].symbol == "AAPL"

def test_list_trades_filters_by_date_range(trade_service: TradeService) -> None:
    """Test that list_trades filters by date range."""
    result = trade_service.list_trades(
        start_date="2026-04-19", end_date=None, symbol=None,
        asset_class=None, buy_sell=None, sort_by="date_time",
        sort_order="desc", page=1, page_size=10,)
    assert len(result.items) == 1
    assert result.items[0].trade_date == "2026-04-19"

def test_list_trades_pagination(trade_service: TradeService) -> None:
    """Test that list_trades paginates correctly."""
    result = trade_service.list_trades(
        start_date=None, end_date=None, symbol=None,
        asset_class=None, buy_sell=None, sort_by="date_time",
        sort_order="desc", page=1, page_size=2,)
    assert len(result.items) == 2
    assert result.pagination.total == 3
    assert result.pagination.total_pages == 2

def test_summarize_trades_returns_aggregate_stats(trade_service: TradeService) -> None:
    """Test that summarize_trades returns correct aggregate statistics."""
    result = trade_service.summarize_trades(
        start_date=None, end_date=None, symbol=None,
        asset_class=None, buy_sell=None,)
    assert result.trade_count == 3
    assert result.buy_count == 2
    assert result.sell_count == 1
    assert result.total_commission == 3.2
    assert result.total_realized_pnl == 25.0
    assert result.symbols_count == 2

def test_summarize_trades_filters_by_symbol(trade_service: TradeService) -> None:
    """Test that summarize_trades filters correctly by symbol."""
    result = trade_service.summarize_trades(
        start_date=None, end_date=None, symbol="AAPL",
        asset_class=None, buy_sell=None,)
    assert result.trade_count == 2
    assert result.symbols_count == 1

def test_summarize_trades_empty_result(trade_service: TradeService) -> None:
    """Test that summarize_trades returns zeros when no trades match."""
    result = trade_service.summarize_trades(
        start_date="2030-01-01", end_date=None, symbol=None,
        asset_class=None, buy_sell=None,)
    assert result.trade_count == 0
    assert result.total_commission == 0.0
