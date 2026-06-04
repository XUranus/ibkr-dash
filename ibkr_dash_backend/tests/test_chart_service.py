"""Tests for the chart service."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.database import Database, init_database
from app.services.chart_service import ChartService


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
def chart_service(db: Database) -> ChartService:
    """Return a ChartService with a seeded database."""
    # Insert account snapshots for equity curve
    for i, (date, equity) in enumerate([
        ("2026-04-15", 95000.0),
        ("2026-04-16", 96000.0),
        ("2026-04-17", 98000.0),
        ("2026-04-18", 100000.0),
    ]):
        db.insert("account_snapshots", {
            "account_id": "U1234567",
            "report_date": date,
            "total_equity": equity,
            "cash": 20000.0,
            "stock_value": equity - 20000.0,
            "cnav_mtm": 1000.0 if i > 0 else None,
            "cnav_twr": 1.0 if i > 0 else None,
        })

    # Insert cash flow
    db.insert("cash_flows", {
        "account_id": "U1234567",
        "date_time": "2026-04-14T12:00:00",
        "settle_date": "2026-04-14",
        "amount": 50000.0,
        "amount_in_base": 50000.0,
        "flow_type": "Deposits/Withdrawals",
        "flow_direction": "deposit",
    })

    return ChartService(db)


def test_equity_curve_returns_items(chart_service: ChartService) -> None:
    """Test that equity curve returns data points."""
    result = chart_service.get_equity_curve(start_date=None, end_date=None)
    assert len(result.items) == 4
    assert result.items[0].report_date == "2026-04-15"
    assert result.items[-1].report_date == "2026-04-18"


def test_equity_curve_filters_by_date(chart_service: ChartService) -> None:
    """Test that equity curve filters by date range."""
    result = chart_service.get_equity_curve(start_date="2026-04-17", end_date=None)
    assert len(result.items) == 2
    assert result.items[0].report_date == "2026-04-17"


def test_equity_curve_computes_total_pnl(chart_service: ChartService) -> None:
    """Test that equity curve computes total PnL correctly."""
    result = chart_service.get_equity_curve(start_date=None, end_date=None)
    # Net cost is 50000 (single deposit), so total_pnl = equity - 50000
    last = result.items[-1]
    assert last.total_equity == 100000.0
    assert last.total_pnl == 50000.0


def test_equity_curve_computes_net_cost(chart_service: ChartService) -> None:
    """Test that equity curve tracks net cost from cash flows."""
    result = chart_service.get_equity_curve(start_date=None, end_date=None)
    # All points should have net_cost = 50000 (deposit on 2026-04-14)
    for item in result.items:
        assert item.net_cost == 50000.0


def test_equity_curve_empty_when_no_data(db: Database) -> None:
    """Test that equity curve returns empty when no data exists."""
    service = ChartService(db)
    result = service.get_equity_curve(start_date=None, end_date=None)
    assert len(result.items) == 0


def test_performance_calendar_month_view(chart_service: ChartService) -> None:
    """Test performance calendar with month view."""
    result = chart_service.get_performance_calendar(view="month", anchor="2026-04")
    assert result.view == "month"
    assert result.anchor == "2026-04"
    assert len(result.items) == 30  # April has 30 days
    # Days with data should have has_data=True
    data_days = [item for item in result.items if item.has_data]
    assert len(data_days) == 4


def test_performance_calendar_year_view(chart_service: ChartService) -> None:
    """Test performance calendar with year view."""
    result = chart_service.get_performance_calendar(view="year", anchor="2026")
    assert result.view == "year"
    assert result.anchor == "2026"
    assert len(result.items) == 12  # 12 months


def test_performance_calendar_all_years_view(chart_service: ChartService) -> None:
    """Test performance calendar with all-years view."""
    result = chart_service.get_performance_calendar(view="all-years", anchor=None)
    assert result.view == "all-years"
    assert result.anchor == "all"


def test_performance_calendar_summary(chart_service: ChartService) -> None:
    """Test that performance calendar includes summary statistics."""
    result = chart_service.get_performance_calendar(view="month", anchor="2026-04")
    assert result.summary is not None
    assert result.summary.periods_with_data == 4


def test_performance_calendar_invalid_view(chart_service: ChartService) -> None:
    """Test that invalid view raises ValueError."""
    with pytest.raises(ValueError, match="view must be one of"):
        chart_service.get_performance_calendar(view="invalid", anchor=None)
