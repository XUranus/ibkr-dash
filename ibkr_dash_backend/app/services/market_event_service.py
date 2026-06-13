"""Market event service: seed and query market events.

Provides pre-seeded macro, central bank, corporate, and market holiday events.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from app.core.database import Database

logger = logging.getLogger(__name__)

# 2025-2026 FOMC meeting dates (8 scheduled meetings per year)
FOMC_DATES_2025 = [
    ("2025-01-29", "2025-01-30"), ("2025-03-18", "2025-03-19"),
    ("2025-05-06", "2025-05-07"), ("2025-06-17", "2025-06-18"),
    ("2025-07-29", "2025-07-30"), ("2025-09-16", "2025-09-17"),
    ("2025-10-28", "2025-10-29"), ("2025-12-16", "2025-12-17"),
]
FOMC_DATES_2026 = [
    ("2026-01-27", "2026-01-28"), ("2026-03-17", "2026-03-18"),
    ("2026-05-05", "2026-05-06"), ("2026-06-16", "2026-06-17"),
    ("2026-07-28", "2026-07-29"), ("2026-09-15", "2026-09-16"),
    ("2026-10-27", "2026-10-28"), ("2026-12-15", "2026-12-16"),
]

# US market holidays 2025-2026
MARKET_HOLIDAYS = [
    ("2025-01-01", "New Year's Day"),
    ("2025-01-20", "Martin Luther King Jr. Day"),
    ("2025-02-17", "Presidents' Day"),
    ("2025-04-18", "Good Friday"),
    ("2025-05-26", "Memorial Day"),
    ("2025-06-19", "Juneteenth"),
    ("2025-07-04", "Independence Day"),
    ("2025-09-01", "Labor Day"),
    ("2025-11-27", "Thanksgiving Day"),
    ("2025-12-25", "Christmas Day"),
    ("2026-01-01", "New Year's Day"),
    ("2026-01-19", "Martin Luther King Jr. Day"),
    ("2026-02-16", "Presidents' Day"),
    ("2026-04-03", "Good Friday"),
    ("2026-05-25", "Memorial Day"),
    ("2026-06-19", "Juneteenth"),
    ("2026-07-03", "Independence Day (observed)"),
    ("2026-09-07", "Labor Day"),
    ("2026-11-26", "Thanksgiving Day"),
    ("2026-12-25", "Christmas Day"),
]

# Key economic data release dates (approximate, for 2026)
# These are typically scheduled months in advance
ECONOMIC_EVENTS_2026 = [
    ("2026-06-06", "NONFARM_PAYROLLS", "Non-Farm Payrolls", "CRITICAL"),
    ("2026-06-11", "CPI", "CPI (May)", "CRITICAL"),
    ("2026-06-25", "GDP", "GDP Q1 Final", "HIGH"),
    ("2026-07-02", "NONFARM_PAYROLLS", "Non-Farm Payrolls", "CRITICAL"),
    ("2026-07-10", "CPI", "CPI (June)", "CRITICAL"),
    ("2026-07-29", "GDP", "GDP Q2 Advance", "HIGH"),
    ("2026-08-07", "NONFARM_PAYROLLS", "Non-Farm Payrolls", "CRITICAL"),
    ("2026-08-12", "CPI", "CPI (July)", "CRITICAL"),
    ("2026-09-04", "NONFARM_PAYROLLS", "Non-Farm Payrolls", "CRITICAL"),
    ("2026-09-10", "CPI", "CPI (August)", "CRITICAL"),
    ("2026-10-02", "NONFARM_PAYROLLS", "Non-Farm Payrolls", "CRITICAL"),
    ("2026-10-13", "CPI", "CPI (September)", "CRITICAL"),
    ("2026-11-06", "NONFARM_PAYROLLS", "Non-Farm Payrolls", "CRITICAL"),
    ("2026-11-10", "CPI", "CPI (October)", "CRITICAL"),
    ("2026-12-04", "NONFARM_PAYROLLS", "Non-Farm Payrolls", "CRITICAL"),
    ("2026-12-10", "CPI", "CPI (November)", "CRITICAL"),
]


def seed_market_events(db: Database) -> int:
    """Seed the market_events table with known events.

    Returns the number of events inserted.
    """
    count = 0

    # FOMC meetings
    for start, end in FOMC_DATES_2025 + FOMC_DATES_2026:
        event_id = f"fomc_{start}"
        db.upsert("market_events", {
            "id": event_id,
            "event_type": "FOMC_RATE_DECISION",
            "category": "FED",
            "title": f"FOMC 会议 ({start} ~ {end})",
            "title_en": f"FOMC Meeting ({start} ~ {end})",
            "scheduled_at": f"{end}T14:00:00",
            "importance": "CRITICAL",
            "source": "SEED",
            "description": "美联储公开市场委员会利率决议",
        }, conflict_cols=["id"])
        count += 1

    # Market holidays
    for dt, name in MARKET_HOLIDAYS:
        event_id = f"holiday_{dt}"
        db.upsert("market_events", {
            "id": event_id,
            "event_type": "MARKET_CLOSED",
            "category": "MARKET",
            "title": f"休市: {name}",
            "title_en": f"Market Closed: {name}",
            "scheduled_at": f"{dt}T09:30:00",
            "importance": "MEDIUM",
            "source": "SEED",
            "description": name,
        }, conflict_cols=["id"])
        count += 1

    # Economic events
    for dt, etype, title, importance in ECONOMIC_EVENTS_2026:
        event_id = f"econ_{dt}_{etype}"
        db.upsert("market_events", {
            "id": event_id,
            "event_type": etype,
            "category": "MACRO",
            "title": title,
            "title_en": title,
            "scheduled_at": f"{dt}T08:30:00",
            "importance": importance,
            "source": "SEED",
            "description": f"美国经济数据发布: {title}",
        }, conflict_cols=["id"])
        count += 1

    logger.info("Seeded %d market events", count)
    return count


def get_upcoming_events(db: Database, days: int = 30, limit: int = 20) -> list[dict]:
    """Get upcoming market events within the next N days."""
    today = date.today().isoformat()
    rows = db.execute(
        """
        SELECT * FROM market_events
        WHERE scheduled_at >= ?
        ORDER BY scheduled_at ASC
        LIMIT ?
        """,
        (f"{today}T00:00:00", limit),
    )
    return rows


def get_today_events(db: Database) -> list[dict]:
    """Get today's market events."""
    today = date.today().isoformat()
    return db.execute(
        "SELECT * FROM market_events WHERE scheduled_at LIKE ? ORDER BY scheduled_at ASC",
        (f"{today}%",),
    )
