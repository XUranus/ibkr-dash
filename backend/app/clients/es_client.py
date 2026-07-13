"""Elasticsearch client compatibility shim backed by SQLite.

This module provides the same interface as the ibkr-show-public ES client,
but stores data in SQLite tables. This allows all repository code copied
from ibkr-show-public to work without modification.

Supported ES operations:
  - search(): match_all, term, range, bool (must/must_not with term/range),
    simple_query_string (substring match), sort, size, from
  - get(): single document by _id
  - index_document(): upsert by _id
  - delete(): remove by _id
  - create_index_if_missing(): create backing table

NOT supported (silently returns empty/wrong results):
  - Aggregations (aggs, terms, histogram, date_histogram, avg, sum, etc.)
  - Nested queries and nested aggregations
  - Script queries and script_score
  - Multi-match, match_phrase, wildcard, regexp, fuzzy queries
  - _source filtering (always returns full _source)
  - Scroll/search_after pagination
  - Highlighting
  - Geo queries

If you need these features, implement them in the _build_where() method
or use a real Elasticsearch instance.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.database import Database

logger = logging.getLogger(__name__)


class ESClientError(RuntimeError):
    """Base Elasticsearch client error."""


class ESUnavailableError(ESClientError):
    """Raised when Elasticsearch is not reachable."""


class ESIndexNotFoundError(ESClientError):
    """Raised when a requested index does not exist."""


class ElasticsearchClient:
    """SQLite-backed drop-in replacement for the Elasticsearch client.

    Each ES "index" maps to a SQLite table with columns:
      - _id TEXT PRIMARY KEY
      - _source TEXT (JSON)
    """

    def __init__(self, settings: Any = None) -> None:
        from app.core.settings_manager import get_manager
        db_path = str(get_manager().get("database.path", "/app/backend/data/ibkr.db"))
        self._db = Database(db_path)

    def _ensure_table(self, index: str) -> None:
        """Create the backing table if it doesn't exist."""
        safe_name = index.replace("-", "_").replace(".", "_")
        self._db.execute(
            f"""CREATE TABLE IF NOT EXISTS es_{safe_name} (
                _id TEXT PRIMARY KEY,
                _source TEXT NOT NULL,
                _created_at TEXT DEFAULT (datetime('now'))
            )"""
        )

    def _table_name(self, index: str) -> str:
        return f"es_{index.replace('-', '_').replace('.', '_')}"

    def ping(self) -> bool:
        try:
            self._db.execute("SELECT 1")
            return True
        except Exception:
            return False

    def search(self, index: str, body: dict | None = None) -> dict:
        """Simplified search that supports basic match_all, term, and range queries."""
        table = self._table_name(index)
        self._ensure_table(index)
        body = body or {}
        query = body.get("query", {})
        size = min(body.get("size", 100), 10000)

        # Build WHERE clause from query
        where_clauses, params = self._build_where(query, table)

        # Sort
        sort_clause = self._build_sort(body.get("sort", []))

        where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        sql = f"SELECT _id, _source FROM {table}{where_sql}{sort_clause} LIMIT ?"
        params.append(size)

        try:
            rows = self._db.execute(sql, tuple(params))
        except Exception:
            return {"hits": {"hits": [], "total": {"value": 0}}}

        hits = []
        for row in rows:
            source = json.loads(row["_source"])
            hits.append({"_id": row["_id"], "_source": source})

        return {
            "hits": {
                "hits": hits,
                "total": {"value": len(hits)},
            }
        }

    def get(self, index: str, id: str) -> dict | None:
        table = self._table_name(index)
        self._ensure_table(index)
        row = self._db.execute_one(f"SELECT _id, _source FROM {table} WHERE _id = ?", (id,))
        if not row:
            return None
        return {"_id": row["_id"], "_source": json.loads(row["_source"])}

    def index_document(self, index: str, id: str, document: dict) -> dict:
        table = self._table_name(index)
        self._ensure_table(index)
        source_json = json.dumps(document, ensure_ascii=False, default=str)
        self._db.upsert(table, {"_id": id, "_source": source_json}, ["_id"])
        return {"_id": id, "result": "ok"}

    def delete(self, index: str, id: str) -> dict:
        table = self._table_name(index)
        self._ensure_table(index)
        with self._db.get_conn() as conn:
            conn.execute(f"DELETE FROM {table} WHERE _id = ?", (id,))
        return {"result": "deleted"}

    def create_index_if_missing(self, index: str, body: dict | None = None) -> None:
        self._ensure_table(index)

    def put_index_settings(self, index: str, settings: dict) -> None:
        pass  # No-op for SQLite

    def update_by_query(self, index: str, body: dict | None = None) -> dict:
        """Simplified update_by_query - just returns 0 updated."""
        return {"updated": 0}

    def count(self, index: str) -> int:
        table = self._table_name(index)
        self._ensure_table(index)
        try:
            row = self._db.execute_one(f"SELECT COUNT(*) as cnt FROM {table}")
            return row["cnt"] if row else 0
        except Exception:
            return 0

    def _build_where(self, query: dict, table: str) -> tuple[list[str], list[Any]]:
        """Build SQL WHERE clauses from an ES query dict."""
        clauses: list[str] = []
        params: list[Any] = []

        if not query or query.get("match_all"):
            return clauses, params

        bool_query = query.get("bool", {})
        filters = bool_query.get("filter", [])
        must = bool_query.get("must", [])

        for f in filters:
            if "term" in f:
                for field, value in f["term"].items():
                    # Search in JSON _source
                    clauses.append(f"json_extract(_source, '$.{field}') = ?")
                    params.append(value)
            elif "range" in f:
                for field, range_spec in f["range"].items():
                    if "gte" in range_spec:
                        clauses.append(f"json_extract(_source, '$.{field}') >= ?")
                        params.append(range_spec["gte"])
                    if "lte" in range_spec:
                        clauses.append(f"json_extract(_source, '$.{field}') <= ?")
                        params.append(range_spec["lte"])
            elif "bool" in f:
                sub_clauses, sub_params = self._build_where({"bool": f["bool"]}, table)
                if sub_clauses:
                    clauses.append(f"({' OR '.join(sub_clauses)})")
                    params.extend(sub_params)

        for m in must:
            if "simple_query_string" in m:
                sq = m["simple_query_string"]
                q = sq.get("query", "")
                fields = sq.get("fields", ["_source"])
                field_clauses = []
                for field in fields:
                    field_clauses.append(f"json_extract(_source, '$.{field}') LIKE ?")
                    params.append(f"%{q}%")
                if field_clauses:
                    clauses.append(f"({' OR '.join(field_clauses)})")

        return clauses, params

    def _build_sort(self, sort: list) -> str:
        if not sort:
            return ""
        parts = []
        for s in sort:
            if isinstance(s, dict):
                for field, order in s.items():
                    direction = "DESC" if order.get("order") == "desc" else "ASC"
                    parts.append(f"json_extract(_source, '$.{field}') {direction}")
            elif isinstance(s, str):
                parts.append(f"json_extract(_source, '$.{s}') ASC")
        return f" ORDER BY {', '.join(parts)}" if parts else ""
