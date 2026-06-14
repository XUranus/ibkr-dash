"""Shared JSON field parsing for database rows."""

from __future__ import annotations

import json


def parse_json_fields(row: dict, fields: list[str]) -> dict:
    """Parse JSON string fields in a database row dict."""
    for field in fields:
        if isinstance(row.get(field), str):
            try:
                row[field] = json.loads(row[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return row
