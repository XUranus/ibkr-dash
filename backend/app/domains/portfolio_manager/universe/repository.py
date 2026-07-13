"""SQLite-backed repository for portfolio universe symbols."""

from __future__ import annotations

from app.core.database import Database
from app.domains.portfolio_manager.common import SQLiteDocStore


def normalize_universe_symbol(symbol: str | None) -> str:
    raw = (symbol or "").strip().upper()
    if not raw:
        return ""
    if "." in raw:
        raw = raw.split(".", 1)[0]
    return raw


class PortfolioUniverseRepository:
    def __init__(self, db: Database) -> None:
        self._store = SQLiteDocStore(db, "pm_universe_symbols", indexed_columns=["symbol", "universe_type", "enabled", "priority", "ai_theme_role", "source"])

    def get_symbol(self, symbol: str) -> dict | None:
        normalized = normalize_universe_symbol(symbol)
        if not normalized:
            return None
        return self._store.get(f"universe:{normalized}")

    def upsert_symbol(self, document: dict) -> dict:
        symbol = normalize_universe_symbol(document.get("symbol"))
        existing = self.get_symbol(symbol) or {}
        display_symbol = document.get("display_symbol") or existing.get("display_symbol") or symbol
        stored = {**existing, **document, "symbol": symbol, "display_symbol": display_symbol}
        return self._store.put(f"universe:{symbol}", stored)

    def bulk_upsert(self, documents: list[dict]) -> list[dict]:
        return [self.upsert_symbol(doc) for doc in documents]

    def disable_symbol(self, symbol: str) -> dict | None:
        existing = self.get_symbol(symbol)
        if existing is None:
            return None
        return self.upsert_symbol({**existing, "enabled": False})

    def list_symbols(
        self,
        *,
        universe_type: str | None = None,
        enabled: bool | None = None,
        priority: str | None = None,
        ai_theme_role: str | None = None,
        theme_tag: str | None = None,
        source: str | None = None,
    ) -> list[dict]:
        filters: dict[str, str | None] = {}
        if universe_type:
            filters["universe_type"] = universe_type
        if enabled is not None:
            filters["enabled"] = "1" if enabled else "0"
        if priority:
            filters["priority"] = priority
        if ai_theme_role:
            filters["ai_theme_role"] = ai_theme_role
        if source:
            filters["source"] = source
        docs = self._store.list_docs(filters=filters if filters else None, limit=1000)
        if theme_tag:
            docs = [d for d in docs if theme_tag in (d.get("theme_tags") or [])]
        return docs
