"""Tests for the chart service."""

from __future__ import annotations

import pytest

from app.core import cache
from app.core.config import Settings
from app.core.database import Database, init_database
from app.services.chart_service import ChartService


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test to avoid cross-test pollution."""
    cache.invalidate_all()
    yield
    cache.invalidate_all()


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
    # Days with computed daily MTM have has_data=True:
    # Apr 15: cnav_mtm=None → no daily MTM
    # Apr 16: cnav_mtm=1000, no prev cumulative → TWR fallback: 95000*1% = 950
    # Apr 17: cnav_mtm=1000, prev=1000 → daily=0 (has data)
    # Apr 18: cnav_mtm=1000, prev=1000 → daily=0 (has data)
    data_days = [item for item in result.items if item.has_data]
    assert len(data_days) == 3


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
    # First day has no cnav_mtm (None).
    # Day 2: cnav_mtm=1000, no prev cumulative → TWR fallback → pnl=950
    # Day 3: cnav_mtm=1000, prev=1000 → daily=0
    # Day 4: cnav_mtm=1000, prev=1000 → daily=0
    assert result.summary.periods_with_data == 3


def test_performance_calendar_invalid_view(chart_service: ChartService) -> None:
    """Test that invalid view raises ValueError."""
    with pytest.raises(ValueError, match="view must be one of"):
        chart_service.get_performance_calendar(view="invalid", anchor=None)


def test_daily_mtm_from_twr_fallback(db: Database) -> None:
    """Test that daily MTM falls back to TWR-based computation.

    When detail fields are zeroed (IBKR API), TWR is the most reliable source.
    daily_mtm = previous_equity * twr / 100
    """
    for date, equity, cummtm, twr in [
        ("2026-06-01", 100000.0, 5000.0, 0.5),
        ("2026-06-02", 103000.0, 8000.0, 3.0),
        ("2026-06-03", 102500.0, 7500.0, -0.5),
    ]:
        db.insert("account_snapshots", {
            "account_id": "U1234567",
            "report_date": date,
            "total_equity": equity,
            "cnav_mtm": cummtm,
            "cnav_twr": twr,
        })

    service = ChartService(db)
    result = service.get_performance_calendar(view="month", anchor="2026-06")
    items_by_date = {item.period_key: item for item in result.items}

    # Day 1: no previous equity → daily_mtm is None
    assert items_by_date["2026-06-01"].pnl is None
    assert items_by_date["2026-06-01"].has_data is False

    # Day 2: TWR=3.0, prev_equity=100000 → 100000 * 3.0 / 100 = 3000
    assert items_by_date["2026-06-02"].pnl == 3000.0
    assert items_by_date["2026-06-02"].has_data is True

    # Day 3: TWR=-0.5, prev_equity=103000 → 103000 * (-0.5) / 100 = -515
    assert items_by_date["2026-06-03"].pnl == -515.0
    assert items_by_date["2026-06-03"].has_data is True


def test_daily_mtm_with_fund_transfer(db: Database) -> None:
    """Test daily MTM with fund transfer uses TWR-based computation.

    TWR-based: 110493.68 * (-2.49) / 100 = -2751.29 (correct daily PnL).
    Cumulative subtraction would give -3517 (wrong without deposit info).
    """
    for date, equity, cummtm, twr, dep in [
        ("2026-06-01", 110493.68, 479.51, 0.44, 0.0),
        ("2026-06-02", 119072.19, 8578.51, -2.49, 11616.15),
    ]:
        db.insert("account_snapshots", {
            "account_id": "U1234567",
            "report_date": date,
            "total_equity": equity,
            "cnav_mtm": cummtm,
            "cnav_twr": twr,
            "cnav_deposits": dep,
        })

    service = ChartService(db)
    result = service.get_performance_calendar(view="month", anchor="2026-06")
    items_by_date = {item.period_key: item for item in result.items}

    # Day 2: TWR=-2.49, prev_equity=110493.68 → 110493.68 * (-2.49) / 100 = -2751.29
    day2 = items_by_date["2026-06-02"]
    assert day2.pnl is not None
    assert day2.pnl == -2751.29
    assert day2.has_data is True
    assert day2.twr == -2.49


def test_twr_from_db_preserved(db: Database) -> None:
    """Test that IBKR's TWR is preserved alongside daily MTM."""
    for date, equity, cummtm, twr_val in [
        ("2026-06-01", 100000.0, 5000.0, 0.5),
        ("2026-06-02", 103000.0, 8000.0, 3.0),
    ]:
        db.insert("account_snapshots", {
            "account_id": "U1234567",
            "report_date": date,
            "total_equity": equity,
            "cnav_mtm": cummtm,
            "cnav_twr": twr_val,
        })

    service = ChartService(db)
    result = service.get_performance_calendar(view="month", anchor="2026-06")
    items_by_date = {item.period_key: item for item in result.items}

    # Day 1: no previous cumulative → skipped
    assert items_by_date["2026-06-01"].twr is None

    # Day 2: TWR from DB (3.0) is preserved
    assert items_by_date["2026-06-02"].twr == 3.0


def test_daily_mtm_from_change_in_unrealized(db: Database) -> None:
    """Test that daily PnL uses changeInUnrealized + realized when available.

    This is the most reliable source for daily PnL, directly from IBKR.
    """
    for date, equity, cummtm, twr, realized, change_unrealized in [
        ("2026-06-01", 110493.68, 479.51, 0.44, 139.03, 457.80),
        ("2026-06-02", 119072.19, 8578.51, -2.49, 0.0, -3037.64),
    ]:
        db.insert("account_snapshots", {
            "account_id": "U1234567",
            "report_date": date,
            "total_equity": equity,
            "cnav_mtm": cummtm,
            "cnav_twr": twr,
            "cnav_deposits": 0.0,
            "cnav_realized": realized,
            "cnav_change_in_unrealized": change_unrealized,
        })

    service = ChartService(db)
    result = service.get_performance_calendar(view="month", anchor="2026-06")
    items_by_date = {item.period_key: item for item in result.items}

    # Day 1: changeInUnrealized + realized = 457.80 + 139.03 = 596.83
    assert items_by_date["2026-06-01"].pnl == 596.83

    # Day 2: changeInUnrealized + realized = -3037.64 + 0 = -3037.64
    assert items_by_date["2026-06-02"].pnl == -3037.64
