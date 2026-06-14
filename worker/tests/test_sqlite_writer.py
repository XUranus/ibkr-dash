"""Tests for the SQLite writer."""

import sqlite3

from worker.writers.sqlite_writer import SqliteWriter


def test_init_schema_creates_tables() -> None:
    """Test that init_schema creates all required tables."""
    writer = SqliteWriter(":memory:")
    writer.init_schema()

    conn = sqlite3.connect(":memory:")
    # We need to check against the writer's in-memory db
    # Since it's :memory:, we use the writer's internal connection
    persistent_conn = writer._connect()

    tables = persistent_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = {row[0] for row in tables}

    assert "account_snapshots" in table_names
    assert "position_snapshots" in table_names
    assert "trade_records" in table_names
    assert "cash_flows" in table_names
    assert "price_history" in table_names


def test_bulk_upsert_account_snapshots() -> None:
    """Test that account snapshots can be upserted."""
    writer = SqliteWriter(":memory:")
    writer.init_schema()

    docs = [
        {
            "_id": "U1234567_2026-04-18",
            "account_id": "U1234567",
            "report_date": "2026-04-18",
            "currency": "USD",
            "total_equity": 100000.0,
            "cash": 20000.0,
            "source_file_name": "test.csv",
            "source_query_type": "daily_snapshot",
        }
    ]

    count = writer.write_account_snapshots(docs)
    assert count == 1

    # Verify the data
    conn = writer._connect()
    rows = conn.execute("SELECT * FROM account_snapshots").fetchall()
    assert len(rows) == 1


def test_bulk_upsert_account_snapshots_updates_on_conflict() -> None:
    """Test that upserting the same account/date updates the existing row."""
    writer = SqliteWriter(":memory:")
    writer.init_schema()

    docs_v1 = [
        {
            "_id": "U1234567_2026-04-18",
            "account_id": "U1234567",
            "report_date": "2026-04-18",
            "total_equity": 100000.0,
        }
    ]
    writer.write_account_snapshots(docs_v1)

    docs_v2 = [
        {
            "_id": "U1234567_2026-04-18",
            "account_id": "U1234567",
            "report_date": "2026-04-18",
            "total_equity": 105000.0,
        }
    ]
    writer.write_account_snapshots(docs_v2)

    conn = writer._connect()
    rows = conn.execute(
        "SELECT total_equity FROM account_snapshots WHERE account_id='U1234567'"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == 105000.0


def test_write_position_snapshots() -> None:
    """Test writing position snapshots."""
    writer = SqliteWriter(":memory:")
    writer.init_schema()

    docs = [
        {
            "_id": "U1234567_2026-04-18_STK_AAPL",
            "account_id": "U1234567",
            "report_date": "2026-04-18",
            "symbol": "AAPL",
            "quantity": 100.0,
            "mark_price": 190.0,
        },
        {
            "_id": "U1234567_2026-04-18_STK_MSFT",
            "account_id": "U1234567",
            "report_date": "2026-04-18",
            "symbol": "MSFT",
            "quantity": 50.0,
            "mark_price": 420.0,
        },
    ]

    count = writer.write_position_snapshots(docs)
    assert count == 2

    conn = writer._connect()
    rows = conn.execute("SELECT symbol FROM position_snapshots ORDER BY symbol").fetchall()
    assert [r[0] for r in rows] == ["AAPL", "MSFT"]


def test_write_trade_records() -> None:
    """Test writing trade records."""
    writer = SqliteWriter(":memory:")
    writer.init_schema()

    docs = [
        {
            "_id": "TX1",
            "account_id": "U1234567",
            "symbol": "AAPL",
            "trade_date": "2026-04-18",
            "buy_sell": "BUY",
            "quantity": 10.0,
            "trade_price": 190.0,
            "transaction_id": "TX1",
        }
    ]

    count = writer.write_trade_records(docs)
    assert count == 1

    conn = writer._connect()
    rows = conn.execute("SELECT * FROM trade_records").fetchall()
    assert len(rows) == 1


def test_write_cash_flows() -> None:
    """Test writing cash flow records."""
    writer = SqliteWriter(":memory:")
    writer.init_schema()

    docs = [
        {
            "_id": "CF1",
            "account_id": "U1234567",
            "date_time": "2026-04-18T12:00:00",
            "amount": 5000.0,
            "flow_type": "Deposits/Withdrawals",
            "transaction_id": "CF1",
        },
        {
            "_id": "CF2",
            "account_id": "U1234567",
            "date_time": "2026-04-18T16:00:00",
            "amount": 12.5,
            "flow_type": "Ordinary Dividend",
            "transaction_id": "CF2",
        },
    ]

    count = writer.write_cash_flows(docs)
    assert count == 2


def test_write_price_history() -> None:
    """Test writing price history records."""
    writer = SqliteWriter(":memory:")
    writer.init_schema()

    docs = [
        {
            "_id": "U1234567_2026-04-17_STK_AAPL",
            "account_id": "U1234567",
            "report_date": "2026-04-17",
            "symbol": "AAPL",
            "close_price": 185.0,
        },
        {
            "_id": "U1234567_2026-04-18_STK_AAPL",
            "account_id": "U1234567",
            "report_date": "2026-04-18",
            "symbol": "AAPL",
            "close_price": 190.0,
            "previous_close_price": 185.0,
        },
    ]

    count = writer.write_price_history(docs)
    assert count == 2


def test_write_empty_lists_returns_zero() -> None:
    """Test that writing empty lists returns 0."""
    writer = SqliteWriter(":memory:")
    writer.init_schema()

    assert writer.write_account_snapshots([]) == 0
    assert writer.write_position_snapshots([]) == 0
    assert writer.write_trade_records([]) == 0
    assert writer.write_cash_flows([]) == 0
    assert writer.write_price_history([]) == 0


def test_write_transform_result_writes_all_types() -> None:
    """Test that write_transform_result writes all document types at once."""
    from worker.parsers.transformers import TransformResult

    writer = SqliteWriter(":memory:")
    writer.init_schema()

    result = TransformResult(
        account_documents=[
            {"_id": "a1", "account_id": "U1", "report_date": "2026-01-01", "total_equity": 100.0}
        ],
        position_documents=[
            {"_id": "p1", "account_id": "U1", "report_date": "2026-01-01", "symbol": "AAPL"}
        ],
        trade_documents=[
            {"_id": "t1", "account_id": "U1", "symbol": "AAPL", "trade_date": "2026-01-01"}
        ],
        cash_flow_documents=[
            {"_id": "c1", "account_id": "U1", "date_time": "2026-01-01T00:00:00", "amount": 100.0}
        ],
        price_history_documents=[
            {"_id": "h1", "account_id": "U1", "report_date": "2026-01-01", "symbol": "AAPL"}
        ],
    )

    counts = writer.write_transform_result(result)
    assert counts["account_snapshots"] == 1
    assert counts["position_snapshots"] == 1
    assert counts["trade_records"] == 1
    assert counts["cash_flows"] == 1
    assert counts["price_history"] == 1
