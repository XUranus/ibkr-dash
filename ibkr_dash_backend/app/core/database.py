"""SQLite database connection and schema management.

Provides a thread-safe connection pool and automatic schema initialization.
All tables use INTEGER PRIMARY KEY (SQLite rowid alias) for efficiency.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path
from typing import Any, Generator

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
-- IBKR financial data (written by worker)
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
    trade_id        TEXT,
    trade_date      TEXT NOT NULL,
    date_time       TEXT,
    settle_date     TEXT,
    transaction_type TEXT,
    exchange        TEXT,
    currency        TEXT DEFAULT 'USD',
    fx_rate_to_base REAL DEFAULT 1.0,
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
    ingested_at     TEXT DEFAULT (datetime('now')),
    UNIQUE(account_id, trade_date, symbol, trade_id)
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

-- AI Agent outputs (written by backend)
CREATE TABLE IF NOT EXISTS trade_reviews (
    id              TEXT PRIMARY KEY,
    review_type     TEXT NOT NULL,
    symbol          TEXT,
    trade_id        TEXT,
    review_output   TEXT NOT NULL,  -- JSON
    metadata        TEXT,           -- JSON
    evidence_summary TEXT,          -- JSON
    run_trace       TEXT,           -- JSON
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS trade_decisions (
    id              TEXT PRIMARY KEY,
    decision_type   TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    decision_output TEXT NOT NULL,  -- JSON
    metadata        TEXT,           -- JSON
    evidence_summary TEXT,          -- JSON
    run_trace       TEXT,           -- JSON
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS daily_position_reviews (
    id              TEXT PRIMARY KEY,
    report_date     TEXT NOT NULL,
    review_output   TEXT NOT NULL,  -- JSON
    metadata        TEXT,           -- JSON
    evidence_summary TEXT,          -- JSON
    run_trace       TEXT,           -- JSON
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS risk_assessments (
    id              TEXT PRIMARY KEY,
    assessment_type TEXT NOT NULL,
    risk_report     TEXT NOT NULL,  -- JSON
    metadata        TEXT,           -- JSON
    run_trace       TEXT,           -- JSON
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Agent infrastructure
CREATE TABLE IF NOT EXISTS agent_prompts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_key      TEXT NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    content         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(prompt_key, version)
);

CREATE TABLE IF NOT EXISTS agent_tasks (
    id              TEXT PRIMARY KEY,
    agent_name      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    progress        TEXT,           -- JSON
    result          TEXT,           -- JSON
    error           TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    started_at      TEXT,
    finished_at     TEXT
);

CREATE TABLE IF NOT EXISTS copilot_sessions (
    id              TEXT PRIMARY KEY,
    title           TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS copilot_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    metadata        TEXT,           -- JSON
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES copilot_sessions(id)
);

CREATE TABLE IF NOT EXISTS copilot_memories (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    memory_type     TEXT NOT NULL,
    content         TEXT NOT NULL,  -- JSON
    status          TEXT DEFAULT 'active',
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES copilot_sessions(id)
);

-- Key-value settings for admin configuration (IBKR, email, etc.)
CREATE TABLE IF NOT EXISTS admin_settings (
    key             TEXT PRIMARY KEY,
    value           TEXT NOT NULL,
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_account_snapshots_date ON account_snapshots(report_date);
CREATE INDEX IF NOT EXISTS idx_position_snapshots_date ON position_snapshots(report_date);
CREATE INDEX IF NOT EXISTS idx_position_snapshots_symbol ON position_snapshots(symbol);
CREATE INDEX IF NOT EXISTS idx_trade_records_date ON trade_records(trade_date);
CREATE INDEX IF NOT EXISTS idx_trade_records_symbol ON trade_records(symbol);
CREATE INDEX IF NOT EXISTS idx_cash_flows_date ON cash_flows(date_time);
CREATE INDEX IF NOT EXISTS idx_price_history_symbol_date ON price_history(symbol, report_date);
CREATE INDEX IF NOT EXISTS idx_copilot_messages_session ON copilot_messages(session_id, created_at);
"""

# Migrations that run after the main schema (safe to re-run)
_MIGRATIONS = [
    "ALTER TABLE copilot_sessions ADD COLUMN title TEXT DEFAULT ''",
    "ALTER TABLE trade_records ADD COLUMN trade_id TEXT",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_trade_records_unique ON trade_records(account_id, trade_date, symbol, trade_id)",
    "ALTER TABLE cash_flows ADD COLUMN flow_direction TEXT",
    "ALTER TABLE position_snapshots ADD COLUMN currency TEXT DEFAULT 'USD'",
    "ALTER TABLE position_snapshots ADD COLUMN fx_rate_to_base REAL DEFAULT 1.0",
    "ALTER TABLE trade_records ADD COLUMN currency TEXT DEFAULT 'USD'",
    "ALTER TABLE trade_records ADD COLUMN fx_rate_to_base REAL DEFAULT 1.0",
    "ALTER TABLE account_snapshots ADD COLUMN cnav_deposits REAL",
    "ALTER TABLE account_snapshots ADD COLUMN cnav_starting_value REAL",
    "ALTER TABLE account_snapshots ADD COLUMN cnav_ending_value REAL",
    "ALTER TABLE account_snapshots ADD COLUMN cnav_realized REAL",
    "ALTER TABLE account_snapshots ADD COLUMN cnav_change_in_unrealized REAL",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_cash_flows_txn_id ON cash_flows(transaction_id) WHERE transaction_id IS NOT NULL AND transaction_id != ''",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_trade_records_dedup ON trade_records(account_id, trade_date, symbol, buy_sell, quantity, trade_price) WHERE trade_id IS NULL OR trade_id = ''",
]


class Database:
    """Thread-safe SQLite database wrapper.

    For in-memory databases (``:memory:``), a single persistent connection is
    held for the lifetime of the ``Database`` instance.  This is necessary
    because ``sqlite3.connect(":memory:")`` creates a *new* database each time,
    and even ``cache=shared`` destroys the database once the last connection
    closes.  Keeping one connection alive ensures ``init_schema()`` and later
    ``execute()`` calls operate on the same data.

    For file-based databases, each operation opens and closes its own
    connection (standard SQLite concurrency with WAL mode).
    """

    def __init__(self, db_path: str | Path) -> None:
        raw = str(db_path)
        self._is_memory = raw == ":memory:" or raw == ""
        self._db_path = ":memory:" if self._is_memory else raw
        self._persistent_conn: sqlite3.Connection | None = None
        if not self._is_memory:
            self._ensure_dir()

    def _ensure_dir(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        """Return a new connection (file DB) or the persistent one (memory DB)."""
        if self._is_memory:
            if self._persistent_conn is None:
                self._persistent_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._persistent_conn.row_factory = sqlite3.Row
                self._persistent_conn.execute("PRAGMA foreign_keys=ON")
            return self._persistent_conn
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def init_schema(self) -> None:
        """Create all tables and indexes if they don't exist."""
        conn = self._connect()
        try:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
            # Run migrations (safe to re-run — errors are ignored)
            for sql in _MIGRATIONS:
                try:
                    conn.execute(sql)
                    conn.commit()
                except sqlite3.OperationalError:
                    pass  # Column already exists
            logger.info("Database schema initialized at %s", self._db_path)
        finally:
            if not self._is_memory:
                conn.close()

    @contextmanager
    def get_conn(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a connection with automatic commit/rollback."""
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if not self._is_memory:
                conn.close()

    def execute(self, sql: str, params: tuple = ()) -> list[dict]:
        """Execute a query and return rows as dicts."""
        with self.get_conn() as conn:
            cursor = conn.execute(sql, params)
            if cursor.description is None:
                return []
            return [dict(row) for row in cursor.fetchall()]

    def execute_one(self, sql: str, params: tuple = ()) -> dict | None:
        """Execute a query and return the first row as a dict."""
        rows = self.execute(sql, params)
        return rows[0] if rows else None

    def insert(self, table: str, data: dict) -> int:
        """Insert a row and return the lastrowid."""
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        with self.get_conn() as conn:
            cursor = conn.execute(sql, tuple(data.values()))
            return cursor.lastrowid  # type: ignore

    def upsert(self, table: str, data: dict, conflict_cols: list[str]) -> None:
        """Insert or update on conflict."""
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        update_set = ", ".join(f"{k}=excluded.{k}" for k in data.keys() if k not in conflict_cols)
        conflict = ", ".join(conflict_cols)
        sql = (
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) "
            f"ON CONFLICT({conflict}) DO UPDATE SET {update_set}"
        )
        with self.get_conn() as conn:
            conn.execute(sql, tuple(data.values()))

    def bulk_upsert(self, table: str, rows: list[dict], conflict_cols: list[str]) -> int:
        """Insert or update multiple rows. Returns count of rows affected."""
        if not rows:
            return 0
        columns = ", ".join(rows[0].keys())
        placeholders = ", ".join("?" for _ in rows[0])
        update_set = ", ".join(f"{k}=excluded.{k}" for k in rows[0].keys() if k not in conflict_cols)
        conflict = ", ".join(conflict_cols)
        sql = (
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) "
            f"ON CONFLICT({conflict}) DO UPDATE SET {update_set}"
        )
        with self.get_conn() as conn:
            count = 0
            for row in rows:
                conn.execute(sql, tuple(row.values()))
                count += 1
            return count


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_db_instance: Database | None = None


def get_database(settings: Settings | None = None) -> Database:
    """Return the singleton database instance."""
    global _db_instance
    if _db_instance is None:
        s = settings or get_settings()
        db_path = s.sqlite_path
        # :memory: must stay as-is (not resolved to a file path)
        if db_path != ":memory:" and not os.path.isabs(db_path):
            db_path = str(Path(__file__).resolve().parents[2] / db_path)
        _db_instance = Database(db_path)
    return _db_instance


def init_database(settings: Settings | None = None) -> Database:
    """Initialize the database schema and return the instance."""
    db = get_database(settings)
    db.init_schema()
    return db
