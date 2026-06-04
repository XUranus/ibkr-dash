"""Database layer tests."""

from __future__ import annotations

from app.core.database import Database


def test_init_schema_creates_tables():
    db = Database(":memory:")
    db.init_schema()

    # Verify key tables exist
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    table_names = [t["name"] for t in tables]

    assert "account_snapshots" in table_names
    assert "position_snapshots" in table_names
    assert "trade_records" in table_names
    assert "cash_flows" in table_names
    assert "price_history" in table_names
    assert "trade_reviews" in table_names
    assert "trade_decisions" in table_names
    assert "daily_position_reviews" in table_names
    assert "risk_assessments" in table_names
    assert "agent_prompts" in table_names
    assert "agent_tasks" in table_names
    assert "copilot_sessions" in table_names
    assert "copilot_messages" in table_names
    assert "copilot_memories" in table_names


def test_insert_and_query():
    db = Database(":memory:")
    db.init_schema()

    db.insert("account_snapshots", {
        "account_id": "U1234567",
        "report_date": "2024-01-15",
        "total_equity": 100000.0,
        "cash": 20000.0,
    })

    rows = db.execute("SELECT * FROM account_snapshots WHERE account_id = ?", ("U1234567",))
    assert len(rows) == 1
    assert rows[0]["total_equity"] == 100000.0


def test_upsert_updates_on_conflict():
    db = Database(":memory:")
    db.init_schema()

    db.upsert("account_snapshots", {
        "account_id": "U1234567",
        "report_date": "2024-01-15",
        "total_equity": 100000.0,
    }, conflict_cols=["account_id", "report_date"])

    db.upsert("account_snapshots", {
        "account_id": "U1234567",
        "report_date": "2024-01-15",
        "total_equity": 105000.0,
    }, conflict_cols=["account_id", "report_date"])

    rows = db.execute("SELECT * FROM account_snapshots")
    assert len(rows) == 1
    assert rows[0]["total_equity"] == 105000.0


def test_bulk_upsert():
    db = Database(":memory:")
    db.init_schema()

    rows_data = [
        {"account_id": "U123", "report_date": "2024-01-15", "symbol": "AAPL", "quantity": 100, "mark_price": 150.0},
        {"account_id": "U123", "report_date": "2024-01-15", "symbol": "MSFT", "quantity": 50, "mark_price": 380.0},
    ]

    count = db.bulk_upsert("position_snapshots", rows_data, conflict_cols=["account_id", "report_date", "symbol"])
    assert count == 2

    rows = db.execute("SELECT * FROM position_snapshots ORDER BY symbol")
    assert len(rows) == 2
    assert rows[0]["symbol"] == "AAPL"
    assert rows[1]["symbol"] == "MSFT"
