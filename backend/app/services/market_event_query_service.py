"""Market event query service for trade decision context.

Provides a structured interface to query market events by symbol,
wrapping the underlying market_event_service database functions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from app.core.database import Database

logger = logging.getLogger(__name__)


@dataclass
class MarketEventItem:
    """A single market event with structured fields."""

    id: str = ""
    title: str = ""
    summary: str = ""
    category: str = ""
    event_type: str = ""
    status: str = ""
    importance: str = ""
    source_code: str = ""
    country: str = ""
    market: str = ""
    symbols: list[str] = field(default_factory=list)
    asset_classes: list[str] = field(default_factory=list)
    scheduled_at: str = ""
    scheduled_timezone: str = ""
    period: str = ""
    is_all_day: bool = False
    is_confirmed_time: bool = False
    has_actual_value: bool = False
    has_forecast_value: bool = False
    values: dict[str, Any] = field(default_factory=dict)
    impacts: list[dict[str, Any]] = field(default_factory=list)
    source_url: str = ""


@dataclass
class MarketEventQueryResult:
    """Result of a market event query."""

    items: list[MarketEventItem] = field(default_factory=list)
    total_count: int = 0
    query_symbol: str = ""
    query_days: int = 30


class MarketEventQueryService:
    """Query market events from the database for trade decision context."""

    def __init__(self, db: Any, settings: Any = None) -> None:
        """Initialize with database and optional settings.

        Args:
            db: Database instance or any object with an execute method.
            settings: Optional settings (unused, kept for compatibility).
        """
        self.db = db
        self.settings = settings

    def get_symbol_events(
        self,
        symbol: str,
        days: int = 30,
        include_macro: bool = True,
    ) -> MarketEventQueryResult:
        """Query market events relevant to a symbol.

        Args:
            symbol: The stock symbol to query events for.
            days: Number of days ahead to look.
            include_macro: Whether to include macro events.

        Returns:
            MarketEventQueryResult with matching events.
        """
        today = date.today()
        end_date = today + timedelta(days=days)
        today_str = today.isoformat()
        end_str = end_date.isoformat()

        items: list[MarketEventItem] = []

        try:
            # Query events that mention this symbol or are macro events
            rows = self.db.execute(
                """
                SELECT * FROM market_events
                WHERE scheduled_at >= ? AND scheduled_at <= ?
                ORDER BY scheduled_at ASC
                """,
                (f"{today_str}T00:00:00", f"{end_str}T23:59:59"),
            )

            base_symbol = symbol.split(".")[0].upper() if symbol else ""

            for row in rows:
                # Check if event is relevant to this symbol
                event_symbols_raw = row.get("symbols") or ""
                if isinstance(event_symbols_raw, str):
                    event_symbols = [s.strip().upper() for s in event_symbols_raw.split(",") if s.strip()]
                elif isinstance(event_symbols_raw, list):
                    event_symbols = [str(s).upper() for s in event_symbols_raw]
                else:
                    event_symbols = []

                category = str(row.get("category") or "").upper()
                is_macro = category in {"MACRO", "FED", "MARKET"}

                # Include if symbol matches or if it's a macro event
                symbol_match = symbol.upper() in event_symbols or base_symbol in event_symbols
                if not symbol_match and not (include_macro and is_macro):
                    continue

                item = MarketEventItem(
                    id=str(row.get("id") or ""),
                    title=str(row.get("title") or ""),
                    summary=str(row.get("summary") or ""),
                    category=str(row.get("category") or ""),
                    event_type=str(row.get("event_type") or ""),
                    status=str(row.get("status") or ""),
                    importance=str(row.get("importance") or ""),
                    source_code=str(row.get("source_code") or ""),
                    country=str(row.get("country") or ""),
                    market=str(row.get("market") or ""),
                    symbols=event_symbols,
                    asset_classes=[str(a).strip() for a in str(row.get("asset_classes") or "").split(",") if a.strip()],
                    scheduled_at=str(row.get("scheduled_at") or ""),
                    scheduled_timezone=str(row.get("scheduled_timezone") or ""),
                    period=str(row.get("period") or ""),
                    is_all_day=bool(row.get("is_all_day")),
                    is_confirmed_time=bool(row.get("is_confirmed_time")),
                    source_url=str(row.get("source_url") or ""),
                )
                items.append(item)

        except Exception as exc:
            logger.warning("MarketEventQueryService: query failed for %s: %s", symbol, exc)

        return MarketEventQueryResult(
            items=items,
            total_count=len(items),
            query_symbol=symbol,
            query_days=days,
        )
