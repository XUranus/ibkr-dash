"""Position service tests."""

from __future__ import annotations

from app.core.database import Database
from app.services.position_service import PositionService


def test_list_positions_empty():
    db = Database(":memory:")
    db.init_schema()
    service = PositionService(db)
    result = service.list_positions(
        report_date=None, symbol=None, asset_class=None,
        sort_by="position_value", sort_order="desc",
        page=1, page_size=20,
    )
    assert result is not None
    assert len(result.items) == 0


def test_list_positions_with_data():
    db = Database(":memory:")
    db.init_schema()

    db.insert("position_snapshots", {
        "account_id": "U123",
        "report_date": "2024-01-15",
        "symbol": "AAPL",
        "quantity": 100,
        "mark_price": 150.0,
        "position_value": 15000.0,
        "percent_of_nav": 15.0,
    })
    db.insert("position_snapshots", {
        "account_id": "U123",
        "report_date": "2024-01-15",
        "symbol": "MSFT",
        "quantity": 50,
        "mark_price": 380.0,
        "position_value": 19000.0,
        "percent_of_nav": 19.0,
    })

    service = PositionService(db)
    result = service.list_positions(
        report_date="2024-01-15", symbol=None, asset_class=None,
        sort_by="position_value", sort_order="desc",
        page=1, page_size=20,
    )
    assert len(result.items) == 2
    assert result.items[0].symbol == "MSFT"  # Higher value first


def test_list_positions_filter_by_symbol():
    db = Database(":memory:")
    db.init_schema()

    db.insert("position_snapshots", {
        "account_id": "U123", "report_date": "2024-01-15",
        "symbol": "AAPL", "quantity": 100, "mark_price": 150.0, "position_value": 15000.0,
    })
    db.insert("position_snapshots", {
        "account_id": "U123", "report_date": "2024-01-15",
        "symbol": "MSFT", "quantity": 50, "mark_price": 380.0, "position_value": 19000.0,
    })

    service = PositionService(db)
    result = service.list_positions(
        report_date="2024-01-15", symbol="AAPL", asset_class=None,
        sort_by="position_value", sort_order="desc",
        page=1, page_size=20,
    )
    assert len(result.items) == 1
    assert result.items[0].symbol == "AAPL"
