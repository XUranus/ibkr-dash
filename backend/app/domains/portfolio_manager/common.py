"""Shared helpers for Portfolio Manager SQLite repositories."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.core.database import Database


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

    def __init__(self, db: Database, table: str, *, indexed_columns: list[str] | None = None) -> None:
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
        where_clauses: list[str] = []
        params: list[Any] = []
        for col, val in (filters or {}).items():
            if val is not None:
                where_clauses.append(f"{col} = ?")
                params.append(val)
        where = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        sql = f"SELECT * FROM {self.table}{where} ORDER BY {order_by} {order_dir} LIMIT ?"
        params.append(limit)
        rows = self.db.execute(sql, tuple(params))
        return [row_to_doc(r) for r in rows]

    def delete(self, doc_id: str) -> None:
        self.db.execute(f"DELETE FROM {self.table} WHERE id = ?", (doc_id,))
