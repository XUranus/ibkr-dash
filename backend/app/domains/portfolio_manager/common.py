"""Shared helpers for Portfolio Manager SQLite repositories."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from app.core.database import Database

# ---------------------------------------------------------------------------
# Action classification constants (single source of truth)
# ---------------------------------------------------------------------------

ADD_LIKE_ACTIONS: set[str] = {
    "add", "add_small", "add_batch", "add_on_pullback", "add_right_side",
    "buy", "build_position", "accumulate", "increase",
}
REDUCE_LIKE_ACTIONS: set[str] = {
    "reduce", "reduce_batch", "reduce_now", "trim_on_rebound",
    "sell", "sell_thesis_broken", "trim",
}
HOLD_LIKE_ACTIONS: set[str] = {
    "hold", "hold_no_add", "wait", "watchlist", "avoid", "panic_blocked", "no_action",
}
ENTRY_BLOCKED_AI_ROLES: set[str] = {"fake_ai_story", "non_ai"}


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def json_loads(text: str | None) -> Any:
    if not text:
        return {}
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}


def dedupe(values: list[str]) -> list[str]:
    """Deduplicate strings preserving order."""
    return list(dict.fromkeys(value for value in values if value))


_TABLE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_VALID_ORDER_DIRS = {"ASC", "DESC"}


def symbol_candidates(symbol: str, display_symbol: str | None = None) -> list[str]:
    """Generate candidate symbol variants for price lookups."""
    # Lazy import to avoid circular dependency
    from app.domains.portfolio_manager.universe.repository import normalize_universe_symbol
    candidates: list[str] = []
    for raw in [symbol, display_symbol, normalize_universe_symbol(symbol)]:
        value = str(raw or "").strip().upper()
        if not value:
            continue
        candidates.append(value)
        base = normalize_universe_symbol(value)
        if base:
            candidates.append(base)
            candidates.append(f"{base}.US")
    return dedupe(candidates)


def row_to_doc(row: dict) -> dict:
    """Convert a SQLite row (with data_json column) back to a full document."""
    data = json_loads(row.get("data_json"))
    data.setdefault("id", row.get("id"))
    data.setdefault("created_at", row.get("created_at"))
    data.setdefault("updated_at", row.get("updated_at"))
    return data


class SQLiteDocStore:
    """Generic document store backed by a SQLite table with a data_json column.

    This replaces the ES client pattern used in the reference project.
    Each document is stored as a row with:
      - id TEXT PRIMARY KEY
      - data_json TEXT (the full document as JSON)
      - created_at / updated_at timestamps
      - optional indexed filter columns
    """

    _VALID_ORDER_DIRS = {"ASC", "DESC"}

    def __init__(self, db: Database, table: str, *, indexed_columns: list[str] | None = None) -> None:
        if not _TABLE_NAME_RE.match(table):
            raise ValueError(f"Invalid table name: {table!r}")
        self.db = db
        self.table = table
        self.indexed_columns = indexed_columns or []

    def get(self, doc_id: str) -> dict | None:
        row = self.db.execute_one(f"SELECT * FROM {self.table} WHERE id = ?", (doc_id,))
        return row_to_doc(row) if row else None

    def put(self, doc_id: str, document: dict) -> dict:
        now = utc_now_iso()
        existing = self.get(doc_id)
        created_at = (existing or {}).get("created_at") or document.get("created_at") or now
        stored = {**document, "id": doc_id, "created_at": created_at, "updated_at": now}
        # Build indexed columns from the document
        indexed = {}
        for col in self.indexed_columns:
            val = stored.get(col)
            if val is not None:
                indexed[col] = val if not isinstance(val, (list, dict)) else json_dumps(val)
        row_data = {"id": doc_id, "data_json": json_dumps(stored), "created_at": created_at, "updated_at": now, **indexed}
        self.db.upsert(self.table, row_data, ["id"])
        return stored

    def list_docs(
        self,
        *,
        filters: dict[str, str | None] | None = None,
        order_by: str = "created_at",
        order_dir: str = "DESC",
        limit: int = 20,
    ) -> list[dict]:
        if not _TABLE_NAME_RE.match(order_by):
            raise ValueError(f"Invalid order_by column: {order_by!r}")
        order_dir_upper = order_dir.upper()
        if order_dir_upper not in self._VALID_ORDER_DIRS:
            raise ValueError(f"Invalid order_dir: {order_dir!r}")
        where_clauses: list[str] = []
        params: list[Any] = []
        for col, val in (filters or {}).items():
            if val is not None:
                if not _TABLE_NAME_RE.match(col):
                    raise ValueError(f"Invalid filter column: {col!r}")
                where_clauses.append(f"{col} = ?")
                params.append(val)
        where = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        sql = f"SELECT * FROM {self.table}{where} ORDER BY {order_by} {order_dir_upper} LIMIT ?"
        params.append(limit)
        rows = self.db.execute(sql, tuple(params))
        return [row_to_doc(r) for r in rows]

    def delete(self, doc_id: str) -> None:
        self.db.execute(f"DELETE FROM {self.table} WHERE id = ?", (doc_id,))
