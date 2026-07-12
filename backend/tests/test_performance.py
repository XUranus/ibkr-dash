"""Tests for the performance domain."""

from __future__ import annotations

import pytest

from app.core.database import Database
from app.domains.performance.service import AccountPerformanceService


@pytest.fixture()
def db():
    """Create an in-memory database with schema."""
    d = Database(":memory:")
    d.init_schema()
    return d


@pytest.fixture()
def svc(db):
    """Create an AccountPerformanceService."""
    return AccountPerformanceService(db)


def _insert_snapshot(db: Database, report_date: str, equity: float, cash: float = 0.0):
    """Helper to insert an account snapshot."""
    db.execute(
        "INSERT INTO account_snapshots (account_id, report_date, total_equity, cash) VALUES (?, ?, ?, ?)",
        ("U1234567", report_date, equity, cash),
    )


def _insert_cashflow(db: Database, date_time: str, amount: float):
    """Helper to insert a cash flow."""
    db.execute(
        "INSERT INTO cash_flows (account_id, date_time, amount, flow_type) VALUES (?, ?, ?, ?)",
        ("U1234567", date_time, amount, "DEPOSIT"),
    )


def test_empty_performance(svc):
    """No data returns missing data quality."""
    result = svc.get_series()
    assert result.summary.data_quality == "missing"
    assert result.series == []


def test_single_snapshot(svc, db):
    """Single snapshot returns one point with no return."""
    _insert_snapshot(db, "2025-01-01", 100000.0)
    result = svc.get_series()
    assert len(result.series) == 1
    assert result.series[0].nav == 100000.0
    assert result.series[0].daily_return is None
    assert result.summary.start_nav == 100000.0
    assert result.summary.end_nav == 100000.0


def test_two_snapshots_no_cashflow(svc, db):
    """Two snapshots with no cash flow: return = NAV change / prev NAV."""
    _insert_snapshot(db, "2025-01-01", 100000.0)
    _insert_snapshot(db, "2025-01-02", 105000.0)
    result = svc.get_series()
    assert len(result.series) == 2
    # Daily return = (105000 - 100000) / 100000 = 0.05
    assert result.series[1].daily_return == pytest.approx(0.05, abs=1e-6)
    assert result.series[1].twr_index is not None
    assert result.summary.twr_total_return is not None


def test_two_snapshots_with_cashflow(svc, db):
    """Cash flow is subtracted from NAV change for return calculation."""
    _insert_snapshot(db, "2025-01-01", 100000.0)
    _insert_cashflow(db, "2025-01-02", 10000.0)  # deposit 10k
    _insert_snapshot(db, "2025-01-02", 115000.0)
    result = svc.get_series()
    assert len(result.series) == 2
    # Adjusted NAV = 115000 - 10000 = 105000
    # Return = (105000 - 100000) / 100000 = 0.05
    assert result.series[1].daily_return == pytest.approx(0.05, abs=1e-6)
    assert result.series[1].net_cash_flow == pytest.approx(10000.0)


def test_max_drawdown(svc, db):
    """Max drawdown is computed from peak to trough."""
    _insert_snapshot(db, "2025-01-01", 100000.0)
    _insert_snapshot(db, "2025-01-02", 110000.0)
    _insert_snapshot(db, "2025-01-03", 99000.0)  # -10% from peak
    _insert_snapshot(db, "2025-01-04", 105000.0)
    result = svc.get_series()
    assert result.summary.max_drawdown is not None
    assert result.summary.max_drawdown < 0


def test_summary_only(svc, db):
    """get_summary returns summary without full series."""
    _insert_snapshot(db, "2025-01-01", 100000.0)
    _insert_snapshot(db, "2025-01-02", 105000.0)
    summary = svc.get_summary()
    assert summary.start_nav == 100000.0
    assert summary.end_nav == 105000.0


def test_date_filter(svc, db):
    """Date filters limit the series."""
    _insert_snapshot(db, "2025-01-01", 100000.0)
    _insert_snapshot(db, "2025-01-02", 105000.0)
    _insert_snapshot(db, "2025-01-03", 110000.0)
    _insert_snapshot(db, "2025-01-04", 115000.0)

    result = svc.get_series(start_date="2025-01-02", end_date="2025-01-03")
    assert len(result.series) == 2
    assert result.series[0].date == "2025-01-02"
    assert result.series[1].date == "2025-01-03"
