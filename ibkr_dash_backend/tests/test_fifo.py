"""Tests for FIFO cost basis computation."""

from __future__ import annotations

import pytest

from app.utils.fifo import compute_fifo_cost_basis, OPTION_MULTIPLIER


def test_empty_trades():
    """Empty trade list returns empty result."""
    assert compute_fifo_cost_basis([]) == {}


def test_single_buy():
    """Single BUY creates a long position."""
    trades = [{"symbol": "AAPL", "asset_class": "STK", "trade_date": "2026-01-01",
               "buy_sell": "BUY", "quantity": 10.0, "trade_price": 150.0}]
    result = compute_fifo_cost_basis(trades)
    assert result["AAPL"]["cost_basis"] == 1500.0
    assert result["AAPL"]["avg_cost"] == 150.0
    assert result["AAPL"]["total_qty"] == 10.0
    assert result["AAPL"]["realized_pnl"] == 0.0


def test_buy_then_sell_full():
    """BUY then SELL closes the position, realized PnL computed."""
    trades = [
        {"symbol": "AAPL", "asset_class": "STK", "trade_date": "2026-01-01",
         "buy_sell": "BUY", "quantity": 10.0, "trade_price": 100.0},
        {"symbol": "AAPL", "asset_class": "STK", "trade_date": "2026-01-02",
         "buy_sell": "SELL", "quantity": 10.0, "trade_price": 120.0},
    ]
    result = compute_fifo_cost_basis(trades)
    # All closed → no open positions → no entry
    assert "AAPL" not in result


def test_buy_then_sell_partial():
    """Partial SELL leaves remaining position."""
    trades = [
        {"symbol": "AAPL", "asset_class": "STK", "trade_date": "2026-01-01",
         "buy_sell": "BUY", "quantity": 10.0, "trade_price": 100.0},
        {"symbol": "AAPL", "asset_class": "STK", "trade_date": "2026-01-02",
         "buy_sell": "SELL", "quantity": 4.0, "trade_price": 120.0},
    ]
    result = compute_fifo_cost_basis(trades)
    assert result["AAPL"]["cost_basis"] == 600.0  # 6 * 100
    assert result["AAPL"]["avg_cost"] == 100.0
    assert result["AAPL"]["total_qty"] == 6.0


def test_multiple_buys_fifo():
    """Multiple BUYs then SELL uses FIFO (first bought, first sold)."""
    trades = [
        {"symbol": "AAPL", "asset_class": "STK", "trade_date": "2026-01-01",
         "buy_sell": "BUY", "quantity": 5.0, "trade_price": 100.0},
        {"symbol": "AAPL", "asset_class": "STK", "trade_date": "2026-01-02",
         "buy_sell": "BUY", "quantity": 5.0, "trade_price": 120.0},
        {"symbol": "AAPL", "asset_class": "STK", "trade_date": "2026-01-03",
         "buy_sell": "SELL", "quantity": 7.0, "trade_price": 130.0},
    ]
    result = compute_fifo_cost_basis(trades)
    # Sold 7: 5 @ 100 + 2 @ 120 = 500 + 240 = 740 cost, 7 * 130 = 910 proceeds
    # Realized = 910 - 740 = 170
    # Remaining: 3 @ 120 = 360
    assert result["AAPL"]["cost_basis"] == 360.0
    assert result["AAPL"]["total_qty"] == 3.0


def test_short_position():
    """SELL to open short, BUY to close short."""
    trades = [
        {"symbol": "PUT", "asset_class": "STK", "trade_date": "2026-01-01",
         "buy_sell": "SELL", "quantity": 10.0, "trade_price": 50.0},
        {"symbol": "PUT", "asset_class": "STK", "trade_date": "2026-01-02",
         "buy_sell": "BUY", "quantity": 10.0, "trade_price": 30.0},
    ]
    result = compute_fifo_cost_basis(trades)
    # Short closed: realized = (50 - 30) * 10 = 200
    # No open positions → no entry
    assert "PUT" not in result


def test_short_position_remaining():
    """Partial close of short position."""
    trades = [
        {"symbol": "PUT", "asset_class": "STK", "trade_date": "2026-01-01",
         "buy_sell": "SELL", "quantity": 10.0, "trade_price": 50.0},
        {"symbol": "PUT", "asset_class": "STK", "trade_date": "2026-01-02",
         "buy_sell": "BUY", "quantity": 4.0, "trade_price": 30.0},
    ]
    result = compute_fifo_cost_basis(trades)
    # Remaining: -6 @ 50, cost = 6 * 50 = 300
    assert result["PUT"]["cost_basis"] == 300.0
    assert result["PUT"]["total_qty"] == -6.0
    assert result["PUT"]["avg_cost"] == 50.0


def test_options_multiplier():
    """Options quantity is multiplied by 100."""
    trades = [
        {"symbol": "CALL", "asset_class": "OPT", "trade_date": "2026-01-01",
         "buy_sell": "BUY", "quantity": 1.0, "trade_price": 5.0},
    ]
    result = compute_fifo_cost_basis(trades)
    # 1 contract * 100 = 100 shares, cost = 100 * 5 = 500
    assert result["CALL"]["cost_basis"] == 500.0
    assert result["CALL"]["total_qty"] == 100.0
    assert result["CALL"]["avg_cost"] == 5.0


def test_options_short():
    """Short option position."""
    trades = [
        {"symbol": "PUT", "asset_class": "OPT", "trade_date": "2026-01-01",
         "buy_sell": "SELL", "quantity": 1.0, "trade_price": 3.0},
    ]
    result = compute_fifo_cost_basis(trades)
    # 1 contract * 100 = -100 shares, cost = 100 * 3 = 300
    assert result["PUT"]["cost_basis"] == 300.0
    assert result["PUT"]["total_qty"] == -100.0
    assert result["PUT"]["avg_cost"] == 3.0


def test_deduplication():
    """Duplicate trades are deduplicated."""
    trades = [
        {"symbol": "AAPL", "asset_class": "STK", "trade_date": "2026-01-01",
         "buy_sell": "BUY", "quantity": 10.0, "trade_price": 100.0},
        {"symbol": "AAPL", "asset_class": "STK", "trade_date": "2026-01-01",
         "buy_sell": "BUY", "quantity": 10.0, "trade_price": 100.0},
    ]
    result = compute_fifo_cost_basis(trades)
    # Deduped: only 1 buy of 10
    assert result["AAPL"]["cost_basis"] == 1000.0
    assert result["AAPL"]["total_qty"] == 10.0


def test_multiple_symbols():
    """Multiple symbols computed independently."""
    trades = [
        {"symbol": "AAPL", "asset_class": "STK", "trade_date": "2026-01-01",
         "buy_sell": "BUY", "quantity": 10.0, "trade_price": 100.0},
        {"symbol": "GOOG", "asset_class": "STK", "trade_date": "2026-01-01",
         "buy_sell": "BUY", "quantity": 5.0, "trade_price": 200.0},
    ]
    result = compute_fifo_cost_basis(trades)
    assert result["AAPL"]["cost_basis"] == 1000.0
    assert result["GOOG"]["cost_basis"] == 1000.0


def test_zero_quantity_skipped():
    """Trades with zero quantity are skipped."""
    trades = [
        {"symbol": "AAPL", "asset_class": "STK", "trade_date": "2026-01-01",
         "buy_sell": "BUY", "quantity": 0.0, "trade_price": 100.0},
    ]
    assert compute_fifo_cost_basis(trades) == {}


def test_zero_price_skipped():
    """Trades with zero price are skipped."""
    trades = [
        {"symbol": "AAPL", "asset_class": "STK", "trade_date": "2026-01-01",
         "buy_sell": "BUY", "quantity": 10.0, "trade_price": 0.0},
    ]
    assert compute_fifo_cost_basis(trades) == {}
