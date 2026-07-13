"""Tests for PortfolioUniverseRepository with SQLite."""

from __future__ import annotations

from app.domains.portfolio_manager.universe.repository import PortfolioUniverseRepository, normalize_universe_symbol
from tests.pm_helpers import make_test_db


def make_repo() -> PortfolioUniverseRepository:
    return PortfolioUniverseRepository(make_test_db())


def test_normalize_symbol() -> None:
    assert normalize_universe_symbol("aapl") == "AAPL"
    assert normalize_universe_symbol("AAPL.US") == "AAPL"
    assert normalize_universe_symbol("") == ""
    assert normalize_universe_symbol(None) == ""


def test_upsert_and_get_symbol() -> None:
    repo = make_repo()
    result = repo.upsert_symbol({"symbol": "AAPL", "display_symbol": "AAPL", "name": "Apple", "universe_type": "holding", "enabled": True})
    assert result["symbol"] == "AAPL"
    fetched = repo.get_symbol("AAPL")
    assert fetched is not None
    assert fetched["name"] == "Apple"


def test_disable_symbol() -> None:
    repo = make_repo()
    repo.upsert_symbol({"symbol": "TSLA", "universe_type": "holding", "enabled": True})
    disabled = repo.disable_symbol("TSLA")
    assert disabled is not None
    assert disabled["enabled"] is False


def test_list_symbols_with_filters() -> None:
    repo = make_repo()
    repo.upsert_symbol({"symbol": "AAPL", "universe_type": "holding", "priority": "high"})
    repo.upsert_symbol({"symbol": "TSLA", "universe_type": "watchlist", "priority": "low"})
    holdings = repo.list_symbols(universe_type="holding")
    assert len(holdings) == 1
    assert holdings[0]["symbol"] == "AAPL"


def test_get_nonexistent_symbol() -> None:
    repo = make_repo()
    assert repo.get_symbol("NONEXISTENT") is None
