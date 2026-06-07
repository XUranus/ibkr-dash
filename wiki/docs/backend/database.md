---
sidebar_position: 3
title: Database
description: SQLite schema, tables, migrations, and query patterns.
---

# Database

The IBKR Dash backend uses **SQLite** as its sole data store. Both the backend (reads) and the worker (writes) share the same `.db` file.

## Schema Overview

The database contains **16 tables** organized into four groups:

### Financial Data (Written by Worker)

These tables store raw IBKR data imported from Flex CSV/XML reports.

| Table | Purpose | Conflict Key |
|-------|---------|--------------|
| `account_snapshots` | Daily account-level equity, cash, and asset breakdown. | `(account_id, report_date)` |
| `position_snapshots` | Per-symbol position snapshots (quantity, price, PnL). | `(account_id, report_date, symbol)` |
| `trade_records` | Individual trade executions (append-only). | `(account_id, trade_date, symbol, trade_id)` |
| `cash_flows` | Deposits, withdrawals, dividends, and other cash movements. | -- |
| `price_history` | Daily OHLC price data per symbol. | `(account_id, report_date, symbol)` |

### AI Agent Outputs (Written by Backend)

| Table | Purpose | Primary Key |
|-------|---------|-------------|
| `trade_reviews` | AI-generated trade review results (JSON). | `id` (UUID) |
| `trade_decisions` | AI-generated trade decision analyses (JSON). | `id` (UUID) |
| `daily_position_reviews` | AI-generated daily portfolio reviews (JSON). | `id` (UUID) |
| `risk_assessments` | AI-generated risk assessment reports (JSON). | `id` (UUID) |

### Agent Infrastructure

| Table | Purpose |
|-------|---------|
| `agent_prompts` | Versioned prompt templates for AI agents. |
| `agent_tasks` | Background task tracking (status, progress, result). |
| `copilot_sessions` | Chat sessions for the Account Copilot. |
| `copilot_messages` | Individual messages within copilot sessions. |
| `copilot_memories` | Persistent memories extracted during copilot conversations. |

### Configuration

| Table | Purpose |
|-------|---------|
| `admin_settings` | Key-value store for admin configuration (IBKR tokens, email settings). |

## Full ER Diagram

This diagram shows all 16 tables with their columns and relationships:

```mermaid
erDiagram
    account_snapshots {
        INTEGER id PK
        TEXT account_id
        TEXT report_date
        TEXT currency
        REAL total_equity
        REAL cash
        REAL stock_value
        REAL options_value
        REAL cnav_mtm
        REAL cnav_twr
        REAL fifo_total_realized_pnl
        REAL fifo_total_unrealized_pnl
    }

    position_snapshots {
        INTEGER id PK
        TEXT account_id FK
        TEXT report_date
        TEXT symbol
        TEXT asset_class
        TEXT currency
        REAL quantity
        REAL mark_price
        REAL position_value
        REAL average_cost_price
        REAL fifo_pnl_unrealized
        REAL total_unrealized_pnl
        REAL total_realized_pnl
        REAL percent_of_nav
        REAL previous_day_change_percent
    }

    trade_records {
        INTEGER id PK
        TEXT account_id FK
        TEXT symbol
        TEXT trade_date
        TEXT trade_id
        TEXT buy_sell
        TEXT asset_class
        TEXT currency
        REAL quantity
        REAL trade_price
        REAL net_cash
        REAL fifo_pnl_realized
        REAL commission
    }

    cash_flows {
        INTEGER id PK
        TEXT account_id FK
        TEXT currency
        TEXT symbol
        TEXT date_time
        REAL amount
        TEXT flow_type
        TEXT flow_direction
        TEXT description
    }

    price_history {
        INTEGER id PK
        TEXT account_id FK
        TEXT report_date
        TEXT symbol
        REAL close_price
        REAL open_price
        REAL high_price
        REAL low_price
    }

    trade_reviews {
        TEXT id PK
        TEXT review_type
        TEXT symbol
        TEXT review_output
        TEXT evidence_summary
        TEXT run_trace
        TEXT created_at
    }

    trade_decisions {
        TEXT id PK
        TEXT decision_type
        TEXT symbol
        TEXT decision_output
        TEXT evidence_summary
        TEXT run_trace
        TEXT created_at
    }

    daily_position_reviews {
        TEXT id PK
        TEXT report_date
        TEXT review_output
        TEXT evidence_summary
        TEXT run_trace
        TEXT created_at
    }

    risk_assessments {
        TEXT id PK
        TEXT assessment_type
        TEXT risk_report
        TEXT run_trace
        TEXT created_at
    }

    agent_prompts {
        INTEGER id PK
        TEXT prompt_key
        INTEGER version
        TEXT content
        TEXT status
        TEXT created_at
    }

    agent_tasks {
        TEXT id PK
        TEXT agent_name
        TEXT status
        TEXT progress
        TEXT result
        TEXT error
        TEXT created_at
        TEXT started_at
        TEXT finished_at
    }

    copilot_sessions {
        TEXT id PK
        TEXT title
        TEXT created_at
    }

    copilot_messages {
        INTEGER id PK
        TEXT session_id FK
        TEXT role
        TEXT content
        TEXT metadata
        TEXT created_at
    }

    copilot_memories {
        TEXT id PK
        TEXT session_id FK
        TEXT memory_type
        TEXT content
        TEXT status
        TEXT created_at
    }

    admin_settings {
        TEXT key PK
        TEXT value
        TEXT updated_at
    }

    account_snapshots ||--o{ position_snapshots : "account_id + report_date"
    account_snapshots ||--o{ trade_records : "account_id"
    account_snapshots ||--o{ cash_flows : "account_id"
    account_snapshots ||--o{ price_history : "account_id + report_date"
    copilot_sessions ||--o{ copilot_messages : "session_id"
    copilot_sessions ||--o{ copilot_memories : "session_id"
```

## Indexes

Indexes are created on the most common query patterns:

```sql
-- From app/core/database.py
CREATE INDEX idx_account_snapshots_date      ON account_snapshots(report_date);
CREATE INDEX idx_position_snapshots_date     ON position_snapshots(report_date);
CREATE INDEX idx_position_snapshots_symbol   ON position_snapshots(symbol);
CREATE INDEX idx_trade_records_date          ON trade_records(trade_date);
CREATE INDEX idx_trade_records_symbol        ON trade_records(symbol);
CREATE INDEX idx_cash_flows_date             ON cash_flows(date_time);
CREATE INDEX idx_price_history_symbol_date   ON price_history(symbol, report_date);
CREATE INDEX idx_copilot_messages_session    ON copilot_messages(session_id, created_at);
```

:::tip
These indexes are designed around the most common query patterns: filtering by date, filtering by symbol, and ordering by session. If you add new query patterns with different filters, consider adding corresponding indexes.
:::

## Migration System

Migrations are defined as a simple list of `ALTER TABLE` / `CREATE INDEX` statements in `app/core/database.py`. They run automatically on startup:

```python
# From app/core/database.py
_MIGRATIONS = [
    "ALTER TABLE copilot_sessions ADD COLUMN title TEXT DEFAULT ''",
    "ALTER TABLE trade_records ADD COLUMN trade_id TEXT",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_trade_records_unique ...",
    "ALTER TABLE cash_flows ADD COLUMN flow_direction TEXT",
]
```

Each migration is wrapped in a `try/except` so that re-running them is safe (column-already-exists errors are silently ignored).

### How to Add a New Migration

To add a new column or index:

1. Open `app/core/database.py`
2. Find the `_MIGRATIONS` list
3. Append your `ALTER TABLE` or `CREATE INDEX` statement
4. The migration runs automatically on the next backend startup

```python
# Example: Adding a new column
_MIGRATIONS = [
    # ... existing migrations ...
    "ALTER TABLE position_snapshots ADD COLUMN sector TEXT DEFAULT ''",
    "CREATE INDEX IF NOT EXISTS idx_position_snapshots_sector ON position_snapshots(sector)",
]
```

:::warning
There is no formal migration framework (like Alembic). Migrations are append-only SQL strings. If you need to add a column, append a new `ALTER TABLE` statement to the `_MIGRATIONS` list. Never modify or remove existing migrations.
:::

## Query Patterns

### Upsert (INSERT or UPDATE)

The `Database.upsert()` method uses SQLite's `ON CONFLICT ... DO UPDATE SET` syntax:

```python
# From app/core/database.py
db.upsert("admin_settings", {"key": "ibkr_flex_token", "value": "abc123"}, conflict_cols=["key"])
```

Generated SQL:
```sql
INSERT INTO admin_settings (key, value) VALUES (?, ?)
ON CONFLICT(key) DO UPDATE SET value = excluded.value
```

### Bulk Upsert

For importing many rows at once (used by the worker):

```python
db.bulk_upsert("position_snapshots", rows, conflict_cols=["account_id", "report_date", "symbol"])
```

### Parameterized Queries

All queries use `?` placeholders to prevent SQL injection:

```python
rows = db.execute(
    "SELECT * FROM position_snapshots WHERE report_date = ? AND symbol = ?",
    ("2025-06-01", "AAPL"),
)
```

:::warning
Never use string formatting (f-strings or `.format()`) to build SQL queries. Always use parameterized queries with `?` placeholders to prevent SQL injection attacks.
:::

### Row Factory

All connections use `sqlite3.Row` as the row factory, so query results are returned as dictionaries:

```python
conn.row_factory = sqlite3.Row
# Later: dict(row) converts Row to a plain dict
```

## Connection Configuration

Every connection applies these PRAGMAs:

```sql
-- From app/core/database.py
PRAGMA journal_mode = WAL;      -- Write-Ahead Logging for concurrent access
PRAGMA foreign_keys = ON;       -- Enforce FK constraints
PRAGMA busy_timeout = 5000;     -- Wait up to 5s if database is locked
```

:::tip
WAL mode is critical because the backend and worker access the same SQLite file concurrently. WAL allows multiple readers to proceed while a single writer is active.
:::

## Why SQLite Over ES/Redis?

The project deliberately chose SQLite to minimize operational complexity:

- **No infrastructure to manage**: No Docker containers for databases, no cluster configuration.
- **Single file backup**: Copy the `.db` file to back up all data.
- **Sufficient performance**: Personal portfolio data (thousands of records) is well within SQLite's capabilities.
- **Full SQL**: Complex queries (aggregations, joins, window functions) are supported natively.
