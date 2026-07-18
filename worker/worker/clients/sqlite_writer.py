"""SQLite writer for IBKR financial data.

Writes parsed/transformed Flex CSV data into the same SQLite database
that the backend reads from.  Uses the schema defined in
backend/app/core/database.py.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)

# Worker-relevant DDL (tables the worker writes to)
_WORKER_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS account_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      TEXT NOT NULL,
    report_date     TEXT NOT NULL,
    currency        TEXT DEFAULT 'USD',
    total_equity    REAL,
    cash            REAL,
    stock_value     REAL,
    options_value   REAL,
    funds_value     REAL,
    crypto_value    REAL,
    cnav_mtm        REAL,
    cnav_twr        REAL,
    cnav_deposits   REAL,
    cnav_starting_value       REAL,
    cnav_ending_value         REAL,
    cnav_realized             REAL,
    cnav_change_in_unrealized REAL,
    fifo_total_realized_pnl   REAL,
    fifo_total_unrealized_pnl REAL,
    raw_json        TEXT,
    ingested_at     TEXT DEFAULT (datetime('now')),
    UNIQUE(account_id, report_date)
);

CREATE TABLE IF NOT EXISTS position_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      TEXT NOT NULL,
    report_date     TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    description     TEXT,
    asset_class     TEXT,
    conid           TEXT,
    isin            TEXT,
    listing_exchange TEXT,
    currency        TEXT DEFAULT 'USD',
    fx_rate_to_base REAL DEFAULT 1.0,
    quantity        REAL,
    mark_price      REAL,
    position_value  REAL,
    average_cost_price REAL,
    cost_basis_money   REAL,
    percent_of_nav  REAL,
    fifo_pnl_unrealized REAL,
    total_realized_pnl  REAL,
    total_unrealized_pnl REAL,
    previous_day_change_percent REAL,
    raw_json        TEXT,
    ingested_at     TEXT DEFAULT (datetime('now')),
    UNIQUE(account_id, report_date, symbol)
);

CREATE TABLE IF NOT EXISTS trade_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    description     TEXT,
    asset_class     TEXT,
    conid           TEXT,
    trade_date      TEXT NOT NULL,
    date_time       TEXT,
    settle_date     TEXT,
    transaction_type TEXT,
    exchange        TEXT,
    quantity        REAL,
    trade_price     REAL,
    trade_money     REAL,
    proceeds        REAL,
    taxes           REAL,
    ib_commission   REAL,
    net_cash        REAL,
    fifo_pnl_realized REAL,
    buy_sell        TEXT,
    order_type      TEXT,
    raw_json        TEXT,
    ingested_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cash_flows (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      TEXT NOT NULL,
    currency        TEXT DEFAULT 'USD',
    symbol          TEXT,
    description     TEXT,
    date_time       TEXT NOT NULL,
    settle_date     TEXT,
    amount          REAL,
    amount_in_base  REAL,
    flow_type       TEXT,
    flow_direction  TEXT,
    dividend_type   TEXT,
    transaction_id  TEXT,
    raw_json        TEXT,
    ingested_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS price_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      TEXT NOT NULL,
    report_date     TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    close_price     REAL,
    open_price      REAL,
    high_price      REAL,
    low_price       REAL,
    previous_close_price REAL,
    raw_json        TEXT,
    ingested_at     TEXT DEFAULT (datetime('now')),
    UNIQUE(account_id, report_date, symbol)
);

CREATE INDEX IF NOT EXISTS idx_account_snapshots_date ON account_snapshots(report_date);
CREATE INDEX IF NOT EXISTS idx_position_snapshots_date ON position_snapshots(report_date);
CREATE INDEX IF NOT EXISTS idx_position_snapshots_symbol ON position_snapshots(symbol);
CREATE INDEX IF NOT EXISTS idx_trade_records_date ON trade_records(trade_date);
CREATE INDEX IF NOT EXISTS idx_trade_records_symbol ON trade_records(symbol);
CREATE INDEX IF NOT EXISTS idx_cash_flows_date ON cash_flows(date_time);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cash_flows_txn_id ON cash_flows(transaction_id) WHERE transaction_id IS NOT NULL AND transaction_id != '';
CREATE INDEX IF NOT EXISTS idx_price_history_symbol_date ON price_history(symbol, report_date);

-- Migration: add currency and fx_rate_to_base to position_snapshots if missing
-- (safe to run repeatedly — ALTER TABLE ADD COLUMN is a no-op if column exists
-- in newer SQLite, but we catch the error for older versions)
"""


class SQLiteWriter:
    """Writes transformed IBKR data into SQLite using upsert semantics."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    @contextmanager
    def _get_conn(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a connection with automatic commit/rollback."""
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        """Create worker-relevant tables and indexes if they don't exist."""
        with self._get_conn() as conn:
            conn.executescript(_WORKER_SCHEMA_SQL)
            # Migration: add columns that may be missing from older schemas
            self._migrate_add_columns(conn)
        logger.info("SQLite schema initialized at %s", self._db_path)

    @staticmethod
    def _migrate_add_columns(conn: sqlite3.Connection) -> None:
        """Add missing columns to existing tables (idempotent)."""
        migrations = [
            ("position_snapshots", "currency", "TEXT DEFAULT 'USD'"),
            ("position_snapshots", "fx_rate_to_base", "REAL DEFAULT 1.0"),
        ]
        for table, column, col_def in migrations:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
            except sqlite3.OperationalError:
                pass  # column already exists

    # ------------------------------------------------------------------
    # Account snapshots
    # ------------------------------------------------------------------

    def bulk_upsert_account_snapshots(self, docs: list[dict]) -> int:
        """Upsert account snapshot records.

        Each doc is a dict produced by the transformers module with an '_id'
        field used as the natural key.  We store the full doc as raw_json and
        populate individual columns from the doc fields.
        """
        if not docs:
            return 0

        sql = """
            INSERT INTO account_snapshots
                (account_id, report_date, currency, total_equity, cash,
                 stock_value, options_value, funds_value, crypto_value,
                 cnav_mtm, cnav_twr, cnav_deposits,
                 cnav_starting_value, cnav_ending_value,
                 cnav_realized, cnav_change_in_unrealized,
                 fifo_total_realized_pnl, fifo_total_unrealized_pnl,
                 raw_json, ingested_at)
            VALUES
                (:account_id, :report_date, :currency, :total_equity, :cash,
                 :stock_value, :options_value, :funds_value, :crypto_value,
                 :cnav_mtm, :cnav_twr, :cnav_deposits,
                 :cnav_starting_value, :cnav_ending_value,
                 :cnav_realized, :cnav_change_in_unrealized,
                 :fifo_total_realized_pnl, :fifo_total_unrealized_pnl,
                 :raw_json, :ingested_at)
            ON CONFLICT(account_id, report_date) DO UPDATE SET
                currency       = excluded.currency,
                total_equity   = excluded.total_equity,
                cash           = excluded.cash,
                stock_value    = excluded.stock_value,
                options_value  = excluded.options_value,
                funds_value    = excluded.funds_value,
                crypto_value   = excluded.crypto_value,
                cnav_mtm       = CASE WHEN excluded.cnav_mtm IS NOT NULL THEN excluded.cnav_mtm ELSE account_snapshots.cnav_mtm END,
                cnav_twr       = CASE WHEN excluded.cnav_twr IS NOT NULL THEN excluded.cnav_twr ELSE account_snapshots.cnav_twr END,
                cnav_deposits  = CASE WHEN excluded.cnav_deposits IS NOT NULL THEN excluded.cnav_deposits ELSE account_snapshots.cnav_deposits END,
                cnav_starting_value       = CASE WHEN excluded.cnav_starting_value IS NOT NULL THEN excluded.cnav_starting_value ELSE account_snapshots.cnav_starting_value END,
                cnav_ending_value         = CASE WHEN excluded.cnav_ending_value IS NOT NULL THEN excluded.cnav_ending_value ELSE account_snapshots.cnav_ending_value END,
                cnav_realized             = CASE WHEN excluded.cnav_realized IS NOT NULL THEN excluded.cnav_realized ELSE account_snapshots.cnav_realized END,
                cnav_change_in_unrealized = CASE WHEN excluded.cnav_change_in_unrealized IS NOT NULL THEN excluded.cnav_change_in_unrealized ELSE account_snapshots.cnav_change_in_unrealized END,
                fifo_total_realized_pnl   = CASE WHEN excluded.fifo_total_realized_pnl IS NOT NULL THEN excluded.fifo_total_realized_pnl ELSE account_snapshots.fifo_total_realized_pnl END,
                fifo_total_unrealized_pnl = CASE WHEN excluded.fifo_total_unrealized_pnl IS NOT NULL THEN excluded.fifo_total_unrealized_pnl ELSE account_snapshots.fifo_total_unrealized_pnl END,
                raw_json       = excluded.raw_json,
                ingested_at    = excluded.ingested_at
        """
        count = 0
        with self._get_conn() as conn:
            for doc in docs:
                row = {
                    "account_id": doc.get("account_id"),
                    "report_date": doc.get("report_date"),
                    "currency": doc.get("currency"),
                    "total_equity": doc.get("total_equity"),
                    "cash": doc.get("cash"),
                    "stock_value": doc.get("stock_value"),
                    "options_value": doc.get("options_value"),
                    "funds_value": doc.get("funds_value"),
                    "crypto_value": doc.get("crypto_value"),
                    "cnav_mtm": doc.get("cnav_mtm"),
                    "cnav_twr": doc.get("cnav_twr"),
                    "cnav_deposits": doc.get("cnav_deposits"),
                    "cnav_starting_value": doc.get("cnav_starting_value"),
                    "cnav_ending_value": doc.get("cnav_ending_value"),
                    "cnav_realized": doc.get("cnav_realized"),
                    "cnav_change_in_unrealized": doc.get("cnav_change_in_unrealized"),
                    "fifo_total_realized_pnl": doc.get("fifo_total_realized_pnl"),
                    "fifo_total_unrealized_pnl": doc.get("fifo_total_unrealized_pnl"),
                    "raw_json": json.dumps(doc, default=str),
                    "ingested_at": doc.get("ingested_at"),
                }
                conn.execute(sql, row)
                count += 1
        logger.info("Upserted %d account_snapshot(s)", count)
        return count

    # ------------------------------------------------------------------
    # Position snapshots
    # ------------------------------------------------------------------

    def bulk_upsert_positions(self, docs: list[dict]) -> int:
        """Upsert position snapshot records.

        Conflict key: (account_id, report_date, symbol).
        """
        if not docs:
            return 0

        sql = """
            INSERT INTO position_snapshots
                (account_id, report_date, symbol, description, asset_class,
                 conid, isin, listing_exchange,
                 currency, fx_rate_to_base,
                 quantity, mark_price, position_value,
                 average_cost_price, cost_basis_money, percent_of_nav,
                 fifo_pnl_unrealized, total_realized_pnl, total_unrealized_pnl,
                 previous_day_change_percent,
                 raw_json, ingested_at)
            VALUES
                (:account_id, :report_date, :symbol, :description, :asset_class,
                 :conid, :isin, :listing_exchange,
                 :currency, :fx_rate_to_base,
                 :quantity, :mark_price, :position_value,
                 :average_cost_price, :cost_basis_money, :percent_of_nav,
                 :fifo_pnl_unrealized, :total_realized_pnl, :total_unrealized_pnl,
                 :previous_day_change_percent,
                 :raw_json, :ingested_at)
            ON CONFLICT(account_id, report_date, symbol) DO UPDATE SET
                description     = excluded.description,
                asset_class     = excluded.asset_class,
                conid           = excluded.conid,
                isin            = excluded.isin,
                listing_exchange = excluded.listing_exchange,
                currency        = excluded.currency,
                fx_rate_to_base = excluded.fx_rate_to_base,
                quantity        = excluded.quantity,
                mark_price      = excluded.mark_price,
                position_value  = excluded.position_value,
                average_cost_price = excluded.average_cost_price,
                cost_basis_money   = CASE WHEN excluded.cost_basis_money IS NOT NULL THEN excluded.cost_basis_money ELSE position_snapshots.cost_basis_money END,
                percent_of_nav  = excluded.percent_of_nav,
                fifo_pnl_unrealized = CASE WHEN excluded.fifo_pnl_unrealized IS NOT NULL THEN excluded.fifo_pnl_unrealized ELSE position_snapshots.fifo_pnl_unrealized END,
                total_realized_pnl  = CASE WHEN excluded.total_realized_pnl IS NOT NULL THEN excluded.total_realized_pnl ELSE position_snapshots.total_realized_pnl END,
                total_unrealized_pnl = CASE WHEN excluded.total_unrealized_pnl IS NOT NULL THEN excluded.total_unrealized_pnl ELSE position_snapshots.total_unrealized_pnl END,
                previous_day_change_percent = excluded.previous_day_change_percent,
                raw_json        = excluded.raw_json,
                ingested_at     = excluded.ingested_at
        """
        count = 0
        with self._get_conn() as conn:
            for doc in docs:
                row = {
                    "account_id": doc.get("account_id"),
                    "report_date": doc.get("report_date"),
                    "symbol": doc.get("symbol"),
                    "description": doc.get("description"),
                    "asset_class": doc.get("asset_class"),
                    "conid": doc.get("conid"),
                    "isin": doc.get("isin"),
                    "listing_exchange": doc.get("listing_exchange"),
                    "currency": doc.get("currency", "USD"),
                    "fx_rate_to_base": doc.get("fx_rate_to_base", 1.0),
                    "quantity": doc.get("quantity"),
                    "mark_price": doc.get("mark_price"),
                    "position_value": doc.get("position_value"),
                    "average_cost_price": doc.get("average_cost_price"),
                    "cost_basis_money": doc.get("cost_basis_money"),
                    "percent_of_nav": doc.get("percent_of_nav"),
                    "fifo_pnl_unrealized": doc.get("fifo_pnl_unrealized"),
                    "total_realized_pnl": doc.get("total_realized_pnl"),
                    "total_unrealized_pnl": doc.get("total_unrealized_pnl"),
                    "previous_day_change_percent": doc.get("previous_day_change_percent"),
                    "raw_json": json.dumps(doc, default=str),
                    "ingested_at": doc.get("ingested_at"),
                }
                conn.execute(sql, row)
                count += 1
        logger.info("Upserted %d position_snapshot(s)", count)
        return count

    # ------------------------------------------------------------------
    # Trade records
    # ------------------------------------------------------------------

    def bulk_upsert_trades(self, docs: list[dict]) -> int:
        """Insert trade records.

        Trade records are append-only (no unique natural key for upsert),
        so we insert each one.  Duplicates are unlikely given the
        transaction_id-based _id in the source.
        """
        if not docs:
            return 0

        sql = """
            INSERT INTO trade_records
                (account_id, symbol, description, asset_class, conid,
                 trade_date, date_time, settle_date,
                 transaction_type, exchange,
                 quantity, trade_price, trade_money,
                 proceeds, taxes, ib_commission, net_cash,
                 fifo_pnl_realized, buy_sell, order_type,
                 raw_json, ingested_at)
            VALUES
                (:account_id, :symbol, :description, :asset_class, :conid,
                 :trade_date, :date_time, :settle_date,
                 :transaction_type, :exchange,
                 :quantity, :trade_price, :trade_money,
                 :proceeds, :taxes, :ib_commission, :net_cash,
                 :fifo_pnl_realized, :buy_sell, :order_type,
                 :raw_json, :ingested_at)
        """
        count = 0
        with self._get_conn() as conn:
            for doc in docs:
                row = {
                    "account_id": doc.get("account_id"),
                    "symbol": doc.get("symbol"),
                    "description": doc.get("description"),
                    "asset_class": doc.get("asset_class"),
                    "conid": doc.get("conid"),
                    "trade_date": doc.get("trade_date"),
                    "date_time": doc.get("date_time"),
                    "settle_date": doc.get("settle_date"),
                    "transaction_type": doc.get("transaction_type"),
                    "exchange": doc.get("exchange"),
                    "quantity": doc.get("quantity"),
                    "trade_price": doc.get("trade_price"),
                    "trade_money": doc.get("trade_money"),
                    "proceeds": doc.get("proceeds"),
                    "taxes": doc.get("taxes"),
                    "ib_commission": doc.get("ib_commission"),
                    "net_cash": doc.get("net_cash"),
                    "fifo_pnl_realized": doc.get("fifo_pnl_realized"),
                    "buy_sell": doc.get("buy_sell"),
                    "order_type": doc.get("order_type"),
                    "raw_json": json.dumps(doc, default=str),
                    "ingested_at": doc.get("ingested_at"),
                }
                conn.execute(sql, row)
                count += 1
        logger.info("Inserted %d trade_record(s)", count)
        return count

    # ------------------------------------------------------------------
    # Cash flows
    # ------------------------------------------------------------------

    def bulk_upsert_cash_flows(self, docs: list[dict]) -> int:
        """Insert cash flow records.

        Cash flows are append-only.
        """
        if not docs:
            return 0

        sql = """
            INSERT INTO cash_flows
                (account_id, currency, symbol, description,
                 date_time, settle_date,
                 amount, amount_in_base,
                 flow_type, flow_direction, dividend_type, transaction_id,
                 raw_json, ingested_at)
            VALUES
                (:account_id, :currency, :symbol, :description,
                 :date_time, :settle_date,
                 :amount, :amount_in_base,
                 :flow_type, :flow_direction, :dividend_type, :transaction_id,
                 :raw_json, :ingested_at)
        """
        count = 0
        with self._get_conn() as conn:
            for doc in docs:
                row = {
                    "account_id": doc.get("account_id"),
                    "currency": doc.get("currency"),
                    "symbol": doc.get("symbol"),
                    "description": doc.get("description"),
                    "date_time": doc.get("date_time"),
                    "settle_date": doc.get("settle_date"),
                    "amount": doc.get("amount"),
                    "amount_in_base": doc.get("amount_in_base"),
                    "flow_type": doc.get("flow_type"),
                    "flow_direction": doc.get("flow_direction"),
                    "dividend_type": doc.get("dividend_type"),
                    "transaction_id": doc.get("transaction_id"),
                    "raw_json": json.dumps(doc, default=str),
                    "ingested_at": doc.get("ingested_at"),
                }
                conn.execute(sql, row)
                count += 1
        logger.info("Inserted %d cash_flow(s)", count)
        return count

    # ------------------------------------------------------------------
    # Price history
    # ------------------------------------------------------------------

    def bulk_upsert_price_history(self, docs: list[dict]) -> int:
        """Upsert price history records.

        Conflict key: (account_id, report_date, symbol).
        """
        if not docs:
            return 0

        sql = """
            INSERT INTO price_history
                (account_id, report_date, symbol,
                 close_price, open_price, high_price, low_price,
                 previous_close_price,
                 raw_json, ingested_at)
            VALUES
                (:account_id, :report_date, :symbol,
                 :close_price, :open_price, :high_price, :low_price,
                 :previous_close_price,
                 :raw_json, :ingested_at)
            ON CONFLICT(account_id, report_date, symbol) DO UPDATE SET
                close_price        = excluded.close_price,
                open_price         = excluded.open_price,
                high_price         = excluded.high_price,
                low_price          = excluded.low_price,
                previous_close_price = excluded.previous_close_price,
                raw_json           = excluded.raw_json,
                ingested_at        = excluded.ingested_at
        """
        count = 0
        with self._get_conn() as conn:
            for doc in docs:
                row = {
                    "account_id": doc.get("account_id"),
                    "report_date": doc.get("report_date"),
                    "symbol": doc.get("symbol"),
                    "close_price": doc.get("close_price"),
                    "open_price": doc.get("open_price"),
                    "high_price": doc.get("high_price"),
                    "low_price": doc.get("low_price"),
                    "previous_close_price": doc.get("previous_close_price"),
                    "raw_json": json.dumps(doc, default=str),
                    "ingested_at": doc.get("ingested_at"),
                }
                conn.execute(sql, row)
                count += 1
        logger.info("Upserted %d price_history record(s)", count)
        return count

    # ------------------------------------------------------------------
    # Single-record helpers (for XML import)
    # ------------------------------------------------------------------

    def upsert_account_snapshot(self, doc: dict) -> None:
        """Upsert a single account snapshot."""
        self.bulk_upsert_account_snapshots([doc])

    def insert_trade(self, doc: dict) -> None:
        """Insert a single trade record (skip if trade_id already exists)."""
        sql = """
            INSERT OR IGNORE INTO trade_records
                (account_id, symbol, description, asset_class, conid, trade_id,
                 trade_date, date_time, settle_date, transaction_type, exchange,
                 quantity, trade_price, trade_money, proceeds, taxes,
                 ib_commission, net_cash, fifo_pnl_realized, buy_sell, order_type,
                 raw_json, ingested_at)
            VALUES
                (:account_id, :symbol, :description, :asset_class, :conid, :trade_id,
                 :trade_date, :date_time, :settle_date, :transaction_type, :exchange,
                 :quantity, :trade_price, :trade_money, :proceeds, :taxes,
                 :ib_commission, :net_cash, :fifo_pnl_realized, :buy_sell, :order_type,
                 :raw_json, :ingested_at)
        """
        row = {
            **doc,
            "raw_json": json.dumps(doc, default=str),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._get_conn() as conn:
            conn.execute(sql, row)

    def insert_cash_flow(self, doc: dict) -> None:
        """Insert a single cash flow record (skip if transaction_id already exists)."""
        sql = """
            INSERT OR IGNORE INTO cash_flows
                (account_id, currency, symbol, description, date_time, settle_date,
                 amount, amount_in_base, flow_type, flow_direction, dividend_type,
                 transaction_id, raw_json, ingested_at)
            VALUES
                (:account_id, :currency, :symbol, :description, :date_time, :settle_date,
                 :amount, :amount_in_base, :flow_type, :flow_direction, :dividend_type,
                 :transaction_id, :raw_json, :ingested_at)
        """
        row = {
            **doc,
            "raw_json": json.dumps(doc, default=str),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._get_conn() as conn:
            conn.execute(sql, row)
