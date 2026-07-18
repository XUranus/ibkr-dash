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
    "CREATE TABLE IF NOT EXISTS position_analysis (id TEXT PRIMARY KEY, report_date TEXT NOT NULL, analysis_zh TEXT NOT NULL, analysis_en TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')))",
    "CREATE INDEX IF NOT EXISTS idx_position_analysis_date ON position_analysis(report_date)",
    "CREATE TABLE IF NOT EXISTS market_events (id TEXT PRIMARY KEY, event_type TEXT NOT NULL, category TEXT NOT NULL, title TEXT NOT NULL, title_en TEXT, scheduled_at TEXT NOT NULL, importance TEXT DEFAULT 'MEDIUM', source TEXT DEFAULT 'MANUAL', description TEXT, created_at TEXT DEFAULT (datetime('now')))",
    "CREATE INDEX IF NOT EXISTS idx_market_events_date ON market_events(scheduled_at)",
    "CREATE TABLE IF NOT EXISTS import_history (id INTEGER PRIMARY KEY AUTOINCREMENT, run_at TEXT DEFAULT (datetime('now')), file_path TEXT NOT NULL, file_size INTEGER DEFAULT 0, status TEXT DEFAULT 'success', records_imported TEXT, error TEXT)",
    "CREATE INDEX IF NOT EXISTS idx_import_history_run_at ON import_history(run_at DESC)",
    "ALTER TABLE import_history ADD COLUMN started_at TEXT",
    "ALTER TABLE import_history ADD COLUMN duration_ms INTEGER DEFAULT 0",
    "CREATE TABLE IF NOT EXISTS agent_replays (replay_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, agent_name TEXT NOT NULL, final_status TEXT DEFAULT 'success', created_at TEXT, payload_json TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS idx_agent_replays_run_id ON agent_replays(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_agent_replays_agent ON agent_replays(agent_name, created_at DESC)",
    "CREATE TABLE IF NOT EXISTS market_event_analysis (id TEXT PRIMARY KEY, content_zh TEXT NOT NULL, content_en TEXT NOT NULL, event_ids TEXT, created_at TEXT DEFAULT (datetime('now')))",
    "CREATE INDEX IF NOT EXISTS idx_market_event_analysis_created ON market_event_analysis(created_at DESC)",
    # Investment policies (Phase 1)
    """CREATE TABLE IF NOT EXISTS investment_policies (
        id              TEXT PRIMARY KEY,
        policy_type     TEXT NOT NULL DEFAULT 'symbol',
        symbol          TEXT,
        risk_profile    TEXT DEFAULT 'balanced',
        asset_role      TEXT DEFAULT 'unknown',
        conviction      TEXT DEFAULT 'medium',
        enabled         INTEGER DEFAULT 1,
        user_preferred_target_position_pct REAL,
        user_preferred_max_position_pct    REAL DEFAULT 0.05,
        user_preferred_min_position_pct    REAL DEFAULT 0.0,
        preferred_add_styles TEXT DEFAULT '[]',
        add_rules       TEXT DEFAULT '[]',
        no_add_triggers TEXT DEFAULT '[]',
        sell_triggers   TEXT DEFAULT '[]',
        hard_constraints TEXT DEFAULT '[]',
        soft_preferences TEXT DEFAULT '[]',
        notes           TEXT DEFAULT '',
        ai_review_status TEXT DEFAULT 'unknown',
        ai_review_summary TEXT,
        ai_review_updated_at TEXT,
        target_annual_return_pct REAL,
        max_drawdown_tolerance_pct REAL,
        allow_concentrated_position INTEGER DEFAULT 0,
        allow_single_position_over_20_pct INTEGER DEFAULT 0,
        allow_leverage  INTEGER DEFAULT 0,
        cash_reserve_pct REAL,
        preferred_sell_style TEXT DEFAULT '',
        holding_period  TEXT DEFAULT '',
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_investment_policies_symbol ON investment_policies(symbol) WHERE symbol IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS idx_investment_policies_type ON investment_policies(policy_type)",
    # LLM call metrics (Phase 2 dependency)
    """CREATE TABLE IF NOT EXISTS llm_call_metrics (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        call_id         TEXT NOT NULL,
        agent_name      TEXT,
        model           TEXT,
        prompt_tokens   INTEGER DEFAULT 0,
        completion_tokens INTEGER DEFAULT 0,
        total_tokens    INTEGER DEFAULT 0,
        latency_ms      INTEGER DEFAULT 0,
        status          TEXT DEFAULT 'success',
        error           TEXT,
        created_at      TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_llm_call_metrics_created ON llm_call_metrics(created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_llm_call_metrics_agent ON llm_call_metrics(agent_name, created_at DESC)",
    # Eval system tables (Phase 3)
    """CREATE TABLE IF NOT EXISTS eval_cases (
        case_id         TEXT PRIMARY KEY,
        agent_name      TEXT NOT NULL,
        source          TEXT DEFAULT 'manual',
        title           TEXT NOT NULL DEFAULT '',
        description     TEXT DEFAULT '',
        notes           TEXT DEFAULT '',
        tags            TEXT DEFAULT '[]',
        enabled         INTEGER DEFAULT 1,
        severity        TEXT DEFAULT 'medium',
        category        TEXT DEFAULT '',
        eval_scope      TEXT DEFAULT 'agent',
        node_name       TEXT DEFAULT '',
        prompt_key      TEXT DEFAULT '',
        prompt_version  TEXT DEFAULT '',
        prompt_hash     TEXT DEFAULT '',
        model           TEXT DEFAULT '',
        source_replay_id TEXT DEFAULT '',
        source_run_id   TEXT DEFAULT '',
        source_llm_call_id TEXT DEFAULT '',
        archived        INTEGER DEFAULT 0,
        archived_at     TEXT,
        archived_reason TEXT DEFAULT '',
        input_json      TEXT DEFAULT '{}',
        expected_json   TEXT DEFAULT '{}',
        metadata_json   TEXT DEFAULT '{}',
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_eval_cases_agent ON eval_cases(agent_name)",
    "CREATE INDEX IF NOT EXISTS idx_eval_cases_source ON eval_cases(source)",
    "CREATE INDEX IF NOT EXISTS idx_eval_cases_scope ON eval_cases(eval_scope)",
    """CREATE TABLE IF NOT EXISTS eval_runs (
        eval_run_id     TEXT PRIMARY KEY,
        name            TEXT DEFAULT '',
        agent_name      TEXT NOT NULL,
        case_ids        TEXT DEFAULT '[]',
        started_at      TEXT,
        finished_at     TEXT,
        status          TEXT DEFAULT 'pending',
        summary_json    TEXT DEFAULT '{}',
        results_json    TEXT DEFAULT '[]',
        config_json     TEXT DEFAULT '{}',
        created_at      TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_eval_runs_agent ON eval_runs(agent_name, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_eval_runs_status ON eval_runs(status)",
    """CREATE TABLE IF NOT EXISTS eval_feedback (
        feedback_id     TEXT PRIMARY KEY,
        source_type     TEXT DEFAULT '',
        source_id       TEXT DEFAULT '',
        agent_name      TEXT DEFAULT '',
        issue_type      TEXT DEFAULT '',
        severity        TEXT DEFAULT 'medium',
        category        TEXT DEFAULT '',
        tags            TEXT DEFAULT '[]',
        status          TEXT DEFAULT 'open',
        replay_id       TEXT DEFAULT '',
        run_id          TEXT DEFAULT '',
        eval_run_id     TEXT DEFAULT '',
        case_id         TEXT DEFAULT '',
        result_case_id  TEXT DEFAULT '',
        converted_case_id TEXT DEFAULT '',
        title           TEXT DEFAULT '',
        description     TEXT DEFAULT '',
        notes           TEXT DEFAULT '',
        evidence_json   TEXT DEFAULT '{}',
        metadata_json   TEXT DEFAULT '{}',
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_eval_feedback_status ON eval_feedback(status)",
    "CREATE INDEX IF NOT EXISTS idx_eval_feedback_agent ON eval_feedback(agent_name)",
    """CREATE TABLE IF NOT EXISTS eval_regression_profiles (
        profile_id      TEXT PRIMARY KEY,
        agent_name      TEXT NOT NULL,
        enabled         INTEGER DEFAULT 1,
        mode            TEXT DEFAULT 'full',
        case_tag        TEXT DEFAULT '',
        severity        TEXT DEFAULT '',
        category        TEXT DEFAULT '',
        include_disabled INTEGER DEFAULT 0,
        include_judge   INTEGER DEFAULT 1,
        include_node_eval INTEGER DEFAULT 0,
        node_name       TEXT DEFAULT '',
        limit_count     INTEGER DEFAULT 100,
        gate_json       TEXT DEFAULT '{}',
        trigger_policy_json TEXT DEFAULT '{}',
        notes           TEXT DEFAULT '',
        version         INTEGER DEFAULT 1,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_eval_regression_profiles_agent ON eval_regression_profiles(agent_name)",
    """CREATE TABLE IF NOT EXISTS eval_regression_gate_reports (
        report_id       TEXT PRIMARY KEY,
        mode            TEXT DEFAULT '',
        trigger_source  TEXT DEFAULT '',
        status          TEXT DEFAULT 'pending',
        ok              INTEGER DEFAULT 0,
        dry_run         INTEGER DEFAULT 0,
        base_ref        TEXT DEFAULT '',
        head_ref        TEXT DEFAULT '',
        changed_files   TEXT DEFAULT '[]',
        impacted_agents TEXT DEFAULT '[]',
        recommended_agents TEXT DEFAULT '[]',
        executed_agents TEXT DEFAULT '[]',
        summary_json    TEXT DEFAULT '{}',
        impact_analysis_json TEXT DEFAULT '{}',
        runs_json       TEXT DEFAULT '[]',
        reasons         TEXT DEFAULT '[]',
        git_json        TEXT DEFAULT '{}',
        metadata_json   TEXT DEFAULT '{}',
        created_by      TEXT DEFAULT '',
        created_at      TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_eval_gate_reports_status ON eval_regression_gate_reports(status)",
    "CREATE INDEX IF NOT EXISTS idx_eval_gate_reports_created ON eval_regression_gate_reports(created_at DESC)",
    # Eval simulation tables
    """CREATE TABLE IF NOT EXISTS eval_simulation_runs (
        simulation_run_id TEXT PRIMARY KEY,
        name TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        agent_names TEXT DEFAULT '[]',
        scenario_ids TEXT DEFAULT '[]',
        started_at TEXT,
        finished_at TEXT,
        summary_json TEXT DEFAULT '{}',
        config_json TEXT DEFAULT '{}',
        metadata_json TEXT DEFAULT '{}',
        created_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_eval_sim_runs_status ON eval_simulation_runs(status)",
    "CREATE INDEX IF NOT EXISTS idx_eval_sim_runs_started ON eval_simulation_runs(started_at DESC)",
    """CREATE TABLE IF NOT EXISTS eval_simulation_results (
        simulation_result_id TEXT PRIMARY KEY,
        simulation_run_id TEXT NOT NULL,
        scenario_id TEXT DEFAULT '',
        agent_name TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        latency_ms INTEGER DEFAULT 0,
        error_code TEXT DEFAULT '',
        source_run_id TEXT DEFAULT '',
        source_task_id TEXT DEFAULT '',
        output_json TEXT DEFAULT '{}',
        output_summary_json TEXT DEFAULT '{}',
        run_trace_json TEXT DEFAULT '{}',
        node_outputs_json TEXT DEFAULT '{}',
        metadata_json TEXT DEFAULT '{}',
        created_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_eval_sim_results_run ON eval_simulation_results(simulation_run_id)",
    # Eval failure mining tables
    """CREATE TABLE IF NOT EXISTS eval_failure_mining_runs (
        failure_mining_run_id TEXT PRIMARY KEY,
        simulation_run_id TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        started_at TEXT,
        finished_at TEXT,
        summary_json TEXT DEFAULT '{}',
        config_json TEXT DEFAULT '{}',
        created_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_eval_fm_runs_status ON eval_failure_mining_runs(status)",
    """CREATE TABLE IF NOT EXISTS eval_failure_items (
        failure_id TEXT PRIMARY KEY,
        failure_mining_run_id TEXT NOT NULL,
        simulation_result_id TEXT DEFAULT '',
        agent_name TEXT DEFAULT '',
        scenario_id TEXT DEFAULT '',
        severity TEXT DEFAULT 'medium',
        category TEXT DEFAULT '',
        error_type TEXT DEFAULT '',
        error_message TEXT DEFAULT '',
        node_name TEXT DEFAULT '',
        details_json TEXT DEFAULT '{}',
        created_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_eval_fm_items_run ON eval_failure_items(failure_mining_run_id)",
    "CREATE INDEX IF NOT EXISTS idx_eval_fm_items_severity ON eval_failure_items(severity)",
    # Eval judge calibration tables
    """CREATE TABLE IF NOT EXISTS eval_judge_calibration_runs (
        calibration_run_id TEXT PRIMARY KEY,
        status TEXT DEFAULT 'pending',
        started_at TEXT,
        finished_at TEXT,
        summary_json TEXT DEFAULT '{}',
        config_json TEXT DEFAULT '{}',
        created_at TEXT DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS eval_judge_calibration_signals (
        signal_id TEXT PRIMARY KEY,
        calibration_run_id TEXT NOT NULL,
        case_id TEXT DEFAULT '',
        agent_name TEXT DEFAULT '',
        expected_label TEXT DEFAULT '',
        actual_label TEXT DEFAULT '',
        judge_score REAL DEFAULT 0,
        correct INTEGER DEFAULT 0,
        details_json TEXT DEFAULT '{}',
        created_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_eval_jc_signals_run ON eval_judge_calibration_signals(calibration_run_id)",
    # Eval baseline health tables
    """CREATE TABLE IF NOT EXISTS eval_baseline_health_reports (
        report_id TEXT PRIMARY KEY,
        status TEXT DEFAULT 'pending',
        agent_name TEXT DEFAULT '',
        overall_score REAL DEFAULT 0,
        recommendations_json TEXT DEFAULT '[]',
        signals_json TEXT DEFAULT '[]',
        summary_json TEXT DEFAULT '{}',
        created_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_eval_bh_reports_agent ON eval_baseline_health_reports(agent_name)",
    # Portfolio Manager domain tables
    """CREATE TABLE IF NOT EXISTS pm_constitution (
        id TEXT PRIMARY KEY, data_json TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS pm_universe_symbols (
        id TEXT PRIMARY KEY, symbol TEXT NOT NULL, universe_type TEXT, enabled TEXT, priority TEXT, ai_theme_role TEXT, source TEXT, data_json TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_pm_universe_symbol ON pm_universe_symbols(symbol)",
    "CREATE INDEX IF NOT EXISTS idx_pm_universe_type ON pm_universe_symbols(universe_type)",
    "CREATE INDEX IF NOT EXISTS idx_pm_universe_enabled ON pm_universe_symbols(enabled)",
    "CREATE INDEX IF NOT EXISTS idx_pm_universe_priority ON pm_universe_symbols(priority)",
    """CREATE TABLE IF NOT EXISTS pm_watchtower_runs (
        id TEXT PRIMARY KEY, run_date TEXT, run_type TEXT, status TEXT, data_json TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_pm_watchtower_runs_date ON pm_watchtower_runs(run_date)",
    """CREATE TABLE IF NOT EXISTS pm_watchtower_items (
        id TEXT PRIMARY KEY, run_id TEXT, run_date TEXT, symbol TEXT, data_json TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_pm_watchtower_items_run ON pm_watchtower_items(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_pm_watchtower_items_symbol ON pm_watchtower_items(symbol)",
    """CREATE TABLE IF NOT EXISTS pm_daily_loop_runs (
        id TEXT PRIMARY KEY, run_date TEXT, run_type TEXT, status TEXT, task_id TEXT, data_json TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_pm_daily_loop_runs_date ON pm_daily_loop_runs(run_date)",
    """CREATE TABLE IF NOT EXISTS pm_auto_decision_runs (
        id TEXT PRIMARY KEY, run_date TEXT, run_type TEXT, status TEXT, data_json TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_pm_auto_decision_runs_date ON pm_auto_decision_runs(run_date)",
    """CREATE TABLE IF NOT EXISTS pm_auto_decision_items (
        id TEXT PRIMARY KEY, run_id TEXT, run_date TEXT, symbol TEXT, selection_status TEXT, data_json TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_pm_auto_decision_items_run ON pm_auto_decision_items(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_pm_auto_decision_items_symbol ON pm_auto_decision_items(symbol)",
    """CREATE TABLE IF NOT EXISTS pm_evaluation_results (
        id TEXT PRIMARY KEY, evaluation_date TEXT, source_type TEXT, symbol TEXT, horizon TEXT, evaluation_label TEXT, source_id TEXT, data_json TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_pm_eval_date ON pm_evaluation_results(evaluation_date)",
    "CREATE INDEX IF NOT EXISTS idx_pm_eval_symbol ON pm_evaluation_results(symbol)",
    """CREATE TABLE IF NOT EXISTS pm_improvement_reports (
        id TEXT PRIMARY KEY, report_date TEXT, report_type TEXT, status TEXT, data_json TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_pm_improvement_date ON pm_improvement_reports(report_date)",
    """CREATE TABLE IF NOT EXISTS pm_portfolio_reports (
        id TEXT PRIMARY KEY, report_date TEXT, report_type TEXT, status TEXT, data_json TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_pm_portfolio_reports_date ON pm_portfolio_reports(report_date)",
    """CREATE TABLE IF NOT EXISTS pm_action_alerts (
        id TEXT PRIMARY KEY, run_date TEXT, symbol TEXT, alert_type TEXT, status TEXT, data_json TEXT NOT NULL, created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_pm_alerts_date ON pm_action_alerts(run_date)",
    "CREATE INDEX IF NOT EXISTS idx_pm_alerts_symbol ON pm_action_alerts(symbol)",
    # API tokens for external access (MCP, integrations)
    """CREATE TABLE IF NOT EXISTS api_tokens (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        token           TEXT NOT NULL UNIQUE,
        name            TEXT NOT NULL DEFAULT '',
        description     TEXT DEFAULT '',
        scopes          TEXT DEFAULT '[]',
        last_used_at    TEXT,
        expires_at      TEXT,
        revoked         INTEGER DEFAULT 0,
        created_at      TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_api_tokens_token ON api_tokens(token)",
    "CREATE INDEX IF NOT EXISTS idx_api_tokens_revoked ON api_tokens(revoked)",
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
