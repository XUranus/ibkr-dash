"""Tests for PriceForwardReturnProvider with SQLite."""

from __future__ import annotations

from app.domains.portfolio_manager.evaluation.outcome_evaluator import PriceForwardReturnProvider
from tests.pm_helpers import make_test_db


def _insert_bars(db, symbol: str, closes: list[float], start_day: int = 1) -> None:
    for index, close in enumerate(closes, start_day):
        db.insert("price_history", {
            "account_id": "test",
            "report_date": f"2026-06-{index:02d}",
            "symbol": symbol,
            "close_price": close,
            "high_price": close * 1.01,
            "low_price": close * 0.99,
        })


def test_price_provider_calculates_forward_drawdown_runup_and_benchmark() -> None:
    db = make_test_db()
    _insert_bars(db, "AMD", [100, 105, 103, 112])
    _insert_bars(db, "SPY", [100, 101, 102, 103])
    provider = PriceForwardReturnProvider(db)

    result = provider.evaluate_forward_return(symbol="AMD", display_symbol="AMD", source_date="2026-06-01", horizon="1d", benchmark_symbol="SPY")

    assert result.price_data_status == "ok"
    assert result.forward_return == 0.05
    assert result.max_drawdown < 0
    assert result.max_runup > 0.05
    assert result.benchmark_return == 0.01
    assert result.benchmark_relative_return == 0.04


def test_price_provider_pending_missing_and_benchmark_missing() -> None:
    db1 = make_test_db()
    _insert_bars(db1, "AMD", [100, 101])
    pending = PriceForwardReturnProvider(db1).evaluate_forward_return(symbol="AMD", display_symbol=None, source_date="2026-06-01", horizon="5d")

    db2 = make_test_db()
    missing = PriceForwardReturnProvider(db2).evaluate_forward_return(symbol="AMD", display_symbol=None, source_date="2026-06-01", horizon="1d")

    db3 = make_test_db()
    _insert_bars(db3, "AMD", [100, 110])
    partial = PriceForwardReturnProvider(db3).evaluate_forward_return(symbol="AMD", display_symbol=None, source_date="2026-06-01", horizon="1d", benchmark_symbol="QQQ")

    assert pending.price_data_status == "pending"
    assert "insufficient_forward_price_history:5d" in pending.data_limitations
    assert missing.price_data_status == "missing"
    assert "price_history_missing:AMD" in missing.data_limitations
    assert partial.price_data_status == "partial"
    assert "price_history_missing:QQQ" in partial.data_limitations
