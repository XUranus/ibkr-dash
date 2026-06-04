"""SQLite writer for IBKR financial data.

Provides bulk upsert methods for writing transformed Flex statement data
into the shared SQLite database used by the backend.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

# Schema DDL for tables the worker writes to.
WORKER_SCHEMA_SQL = """
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
    interest_accruals REAL,
    dividend_accruals REAL,
    margin_financing_charge_accruals REAL,
    cnav_starting_value REAL,
    cnav_ending_value   REAL,
    cnav_mtm        REAL,
    cnav_realized   REAL,
    cnav_change_in_unrealized REAL,
    cnav_dividends  REAL,
    cnav_interest   REAL,
    cnav_commissions REAL,
    cnav_broker_fees REAL,
    cnav_net_fx_trading REAL,
    cnav_twr        REAL,
    crtt_dividends_mtd REAL,
    crtt_dividends_ytd REAL,
    crtt_broker_interest_mtd REAL,
    crtt_broker_interest_ytd REAL,
    crtt_commissions_mtd REAL,
    crtt_commissions_ytd REAL,
    crtt_starting_cash REAL,
    crtt_ending_cash REAL,
    fifo_total_realized_pnl   REAL,
    fifo_total_unrealized_pnl REAL,
    fifo_total_pnl  REAL,
    source_file_name TEXT,
    source_query_type TEXT,
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
    sub_category    TEXT,
    conid           TEXT,
    isin            TEXT,
    figi            TEXT,
    listing_exchange TEXT,
    issuer          TEXT,
    issuer_country_code TEXT,
    quantity        REAL,
    mark_price      REAL,
    position_value  REAL,
    open_price      REAL,
    cost_basis_price REAL,
    average_cost_price REAL,
    cost_basis_money   REAL,
    percent_of_nav  REAL,
    fifo_pnl_unrealized REAL,
    side            TEXT,
    shares_at_ib    REAL,
    shares_borrowed REAL,
    shares_lent     REAL,
    net_shares      REAL,
    total_realized_pnl  REAL,
    realized_pnl_percent REAL,
    total_unrealized_pnl REAL,
    unrealized_pnl_percent REAL,
    total_fifo_pnl  REAL,
    previous_day_change_percent REAL,
    realized_pnl_mtd REAL,
    realized_pnl_ytd REAL,
    mark_to_market_mtd REAL,
    mark_to_market_ytd REAL,
    source_file_name TEXT,
    source_query_type TEXT,
    raw_json        TEXT,
    ingested_at     TEXT DEFAULT (datetime('now')),
    UNIQUE(account_id, report_date, symbol)
);

CREATE TABLE IF NOT EXISTS trade_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      TEXT NOT NULL,
    currency        TEXT,
    asset_class     TEXT,
    sub_category    TEXT,
    symbol          TEXT NOT NULL,
    description     TEXT,
    conid           TEXT,
    isin            TEXT,
    figi            TEXT,
    listing_exchange TEXT,
    trade_id        TEXT,
    related_trade_id TEXT,
    report_date     TEXT,
    trade_date      TEXT NOT NULL,
    date_time       TEXT,
    settle_date_target TEXT,
    transaction_type TEXT,
    exchange        TEXT,
    quantity        REAL,
    trade_price     REAL,
    trade_money     REAL,
    proceeds        REAL,
    taxes           REAL,
    ib_commission   REAL,
    ib_commission_currency TEXT,
    net_cash        REAL,
    close_price     REAL,
    open_close_indicator TEXT,
    notes_codes     TEXT,
    cost_basis      REAL,
    fifo_pnl_realized REAL,
    mtm_pnl         REAL,
    orig_trade_price REAL,
    orig_trade_date TEXT,
    orig_trade_id   TEXT,
    orig_order_id   TEXT,
    orig_transaction_id TEXT,
    buy_sell        TEXT,
    ib_order_id     TEXT,
    transaction_id  TEXT,
    ib_exec_id      TEXT,
    related_transaction_id TEXT,
    brokerage_order_id TEXT,
    order_reference TEXT,
    exch_order_id   TEXT,
    ext_exec_id     TEXT,
    order_time      TEXT,
    open_date_time  TEXT,
    holding_period_date_time TEXT,
    when_realized   TEXT,
    when_reopened   TEXT,
    order_type      TEXT,
    trader_id       TEXT,
    is_api_order    INTEGER,
    accrued_interest REAL,
    initial_investment REAL,
    unbc_total_commission REAL,
    unbc_broker_execution_charge REAL,
    unbc_broker_clearing_charge REAL,
    unbc_third_party_execution_charge REAL,
    unbc_third_party_clearing_charge REAL,
    unbc_third_party_regulatory_charge REAL,
    unbc_reg_finra_trading_activity_fee REAL,
    unbc_reg_section31_transaction_fee REAL,
    unbc_reg_other  REAL,
    unbc_other      REAL,
    source_file_name TEXT,
    source_query_type TEXT,
    raw_json        TEXT,
    ingested_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cash_flows (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      TEXT NOT NULL,
    currency        TEXT DEFAULT 'USD',
    asset_class     TEXT,
    sub_category    TEXT,
    symbol          TEXT,
    description     TEXT,
    date_time       TEXT NOT NULL,
    settle_date     TEXT,
    available_for_trading_date TEXT,
    amount          REAL,
    fx_rate_to_base REAL,
    amount_in_base  REAL,
    flow_direction  TEXT,
    flow_type       TEXT,
    dividend_type   TEXT,
    transaction_id  TEXT,
    trade_id        TEXT,
    code            TEXT,
    report_date     TEXT,
    ex_date         TEXT,
    client_reference TEXT,
    action_id       TEXT,
    level_of_detail TEXT,
    source_file_name TEXT,
    source_query_type TEXT,
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
    prior_mtm_pnl  REAL,
    conid           TEXT,
    isin            TEXT,
    raw_json        TEXT,
    ingested_at     TEXT DEFAULT (datetime('now')),
    UNIQUE(account_id, report_date, symbol)
);
"""


class SqliteWriter:
    """Writes transformed IBKR data into a SQLite database.

    Uses bulk upsert operations to insert or update rows. Each upsert
    stores the full document as raw_json for debugging.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._is_memory = self._db_path == ":memory:"
        self._persistent_conn: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        """Return a connection to the database."""
        if self._is_memory:
            if self._persistent_conn is None:
                self._persistent_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._persistent_conn.row_factory = sqlite3.Row
                self._persistent_conn.execute("PRAGMA foreign_keys=ON")
            return self._persistent_conn
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def init_schema(self) -> None:
        """Create all worker tables if they do not already exist."""
        conn = self._connect()
        try:
            conn.executescript(WORKER_SCHEMA_SQL)
            conn.commit()
            logger.info("Worker schema initialized at %s", self._db_path)
        finally:
            if not self._is_memory:
                conn.close()

    def _bulk_upsert(
        self,
        conn: sqlite3.Connection,
        table: str,
        rows: list[dict],
        conflict_cols: list[str],
    ) -> int:
        """Insert or update multiple rows. Returns count of rows processed."""
        if not rows:
            return 0

        first = rows[0]
        columns = list(first.keys())
        placeholders = ", ".join("?" for _ in columns)
        update_set = ", ".join(
            f"{k}=excluded.{k}" for k in columns if k not in conflict_cols
        )
        conflict = ", ".join(conflict_cols)
        sql = (
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "
            f"ON CONFLICT({conflict}) DO UPDATE SET {update_set}"
        )

        count = 0
        for row in rows:
            values = []
            for col in columns:
                val = row.get(col)
                # Serialize dicts/lists as JSON for raw_json column
                if isinstance(val, (dict, list)):
                    val = json.dumps(val)
                values.append(val)
            conn.execute(sql, tuple(values))
            count += 1
        return count

    def write_account_snapshots(self, documents: list[dict]) -> int:
        """Upsert account snapshot documents. Returns count written."""
        if not documents:
            return 0
        conn = self._connect()
        try:
            count = self._bulk_upsert(
                conn, "account_snapshots", documents, ["account_id", "report_date"]
            )
            conn.commit()
            logger.info("upserted %d account snapshots", count)
            return count
        finally:
            if not self._is_memory:
                conn.close()

    def write_position_snapshots(self, documents: list[dict]) -> int:
        """Upsert position snapshot documents. Returns count written."""
        if not documents:
            return 0
        conn = self._connect()
        try:
            count = self._bulk_upsert(
                conn, "position_snapshots", documents, ["account_id", "report_date", "symbol"]
            )
            conn.commit()
            logger.info("upserted %d position snapshots", count)
            return count
        finally:
            if not self._is_memory:
                conn.close()

    def write_trade_records(self, documents: list[dict]) -> int:
        """Insert trade records. Returns count written.

        Trades are append-only (no upsert conflict columns) since each
        trade has a unique transaction ID or composite key.
        """
        if not documents:
            return 0
        conn = self._connect()
        try:
            first = documents[0]
            columns = list(first.keys())
            placeholders = ", ".join("?" for _ in columns)
            sql = f"INSERT INTO trade_records ({', '.join(columns)}) VALUES ({placeholders})"

            count = 0
            for row in documents:
                values = []
                for col in columns:
                    val = row.get(col)
                    if isinstance(val, (dict, list)):
                        val = json.dumps(val)
                    values.append(val)
                conn.execute(sql, tuple(values))
                count += 1
            conn.commit()
            logger.info("inserted %d trade records", count)
            return count
        finally:
            if not self._is_memory:
                conn.close()

    def write_cash_flows(self, documents: list[dict]) -> int:
        """Insert cash flow records. Returns count written."""
        if not documents:
            return 0
        conn = self._connect()
        try:
            first = documents[0]
            columns = list(first.keys())
            placeholders = ", ".join("?" for _ in columns)
            sql = f"INSERT INTO cash_flows ({', '.join(columns)}) VALUES ({placeholders})"

            count = 0
            for row in documents:
                values = []
                for col in columns:
                    val = row.get(col)
                    if isinstance(val, (dict, list)):
                        val = json.dumps(val)
                    values.append(val)
                conn.execute(sql, tuple(values))
                count += 1
            conn.commit()
            logger.info("inserted %d cash flows", count)
            return count
        finally:
            if not self._is_memory:
                conn.close()

    def write_price_history(self, documents: list[dict]) -> int:
        """Upsert price history documents. Returns count written."""
        if not documents:
            return 0
        conn = self._connect()
        try:
            count = self._bulk_upsert(
                conn, "price_history", documents, ["account_id", "report_date", "symbol"]
            )
            conn.commit()
            logger.info("upserted %d price history records", count)
            return count
        finally:
            if not self._is_memory:
                conn.close()

    def write_transform_result(self, result) -> dict[str, int]:
        """Write all document types from a TransformResult.

        Args:
            result: A TransformResult with account_documents, position_documents,
                    trade_documents, cash_flow_documents, price_history_documents.

        Returns:
            A dict with counts for each document type.
        """
        return {
            "account_snapshots": self.write_account_snapshots(result.account_documents),
            "position_snapshots": self.write_position_snapshots(result.position_documents),
            "trade_records": self.write_trade_records(result.trade_documents),
            "cash_flows": self.write_cash_flows(result.cash_flow_documents),
            "price_history": self.write_price_history(result.price_history_documents),
        }
