"""Market event service: fetch, seed, and query market events.

Data sources:
1. Federal Reserve FOMC calendar (scraped from federalreserve.gov)
2. BLS release calendar (API, requires key)
3. Pre-seeded market holidays (fallback)
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from typing import Any

import httpx

from app.core.database import Database

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 15.0
HTTP_HEADERS = {
    "User-Agent": "ibkr-dash/1.0 (market-event-calendar)",
    "Accept": "text/html,application/json,*/*;q=0.8",
}

# US market holidays 2025-2026 (fallback)
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


# ---------------------------------------------------------------------------
# Fed FOMC provider (no API key needed)
# ---------------------------------------------------------------------------

FOMC_CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def _fetch_fomc_events() -> list[dict]:
    """Scrape FOMC meeting dates from federalreserve.gov.

    Returns list of event dicts. Returns empty list on failure
    (network error, parse failure, or no meetings found).
    """
    events = []
    try:
        resp = httpx.get(FOMC_CALENDAR_URL, headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        html = resp.text
    except httpx.HTTPStatusError as exc:
        logger.warning("FOMC calendar HTTP error %s: %s", exc.response.status_code, exc)
        return events
    except httpx.RequestError as exc:
        logger.warning("FOMC calendar request failed: %s", exc)
        return events
    except Exception as exc:
        logger.warning("Unexpected error fetching FOMC calendar: %s", exc)
        return events

    if not html or len(html) < 100:
        logger.warning("FOMC calendar response too short (%d chars), may be blocked", len(html))
        return events

    try:
        # Strip scripts/styles, extract text
        text = re.sub(r"<script\b.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = text.replace("\xa0", " ")
        text = re.sub(r"\s+", " ", text)

        # Find year sections and meeting dates
        year_pattern = re.compile(r"\b(?P<year>20\d{2})\s+FOMC\s+Meetings\b", re.IGNORECASE)
        date_pattern = re.compile(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)"
            r"\s+(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?",
            re.IGNORECASE,
        )

        for year_match in year_pattern.finditer(text):
            current_year = int(year_match.group("year"))
            section_start = year_match.end()
            next_year = year_pattern.search(text[section_start:])
            section = text[section_start:section_start + next_year.start()] if next_year else text[section_start:]

            for date_match in date_pattern.finditer(section):
                month_name = date_match.group(1)
                day_start = int(date_match.group(2))
                day_end = int(date_match.group(3)) if date_match.group(3) else day_start
                month_num = MONTH_MAP.get(month_name.lower())
                if not month_num:
                    continue

                scheduled = datetime(current_year, month_num, day_end, 18, 0, 0, tzinfo=timezone.utc)

                events.append({
                    "id": f"fomc_{current_year}_{month_num:02d}_{day_end:02d}",
                    "event_type": "FOMC_RATE_DECISION",
                    "category": "FED",
                    "title": f"FOMC {month_name} {current_year}",
                    "title_en": f"FOMC Meeting {month_name} {current_year}",
                    "scheduled_at": scheduled.isoformat(),
                    "importance": "CRITICAL",
                    "source": "FED",
                    "description": "美联储公开市场委员会利率决议",
                })

    except Exception as exc:
        logger.warning("Failed to parse FOMC calendar HTML: %s", exc)
        return []

    if not events:
        logger.warning("FOMC scraper found 0 events — page structure may have changed")
    else:
        logger.info("Fetched %d FOMC events from Fed", len(events))
    return events


# ---------------------------------------------------------------------------
# BLS provider (requires API key)
# ---------------------------------------------------------------------------

BLS_CALENDAR_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_SERIES = {
    "CUUR0000SA0": ("CPI", "CPI", "CRITICAL"),
    "WPUFD4": ("PPI", "PPI", "HIGH"),
    "CES0000000001": ("Nonfarm Payrolls", "NONFARM_PAYROLLS", "CRITICAL"),
    "LNS14000000": ("Unemployment Rate", "UNEMPLOYMENT_RATE", "CRITICAL"),
}


def _fetch_bls_events(api_key: str | None = None) -> list[dict]:
    """Fetch BLS release dates via API. Requires API key for full access."""
    if not api_key:
        logger.info("BLS API key not configured, skipping BLS events")
        return []

    events = []
    for series_id, (name, event_type, importance) in BLS_SERIES.items():
        try:
            resp = httpx.get(
                f"{BLS_CALENDAR_URL}{series_id}",
                params={"latest": "true", "registrationkey": api_key},
                headers=HTTP_HEADERS,
                timeout=HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            # BLS API returns data but not release dates directly
            # We'd need to parse the response to get the latest value date
            # For now, skip if no release schedule endpoint
        except Exception as exc:
            logger.warning("Failed to fetch BLS series %s: %s", series_id, exc)

    return events


# ---------------------------------------------------------------------------
# Seed and sync
# ---------------------------------------------------------------------------

def seed_market_events(db: Database) -> int:
    """Seed market events: market holidays + FOMC from Fed."""
    count = 0

    # Market holidays (pre-seeded)
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

    # FOMC events from Fed website
    fomc_events = _fetch_fomc_events()
    for event in fomc_events:
        db.upsert("market_events", event, conflict_cols=["id"])
        count += 1

    logger.info("Seeded %d market events", count)
    return count


def sync_market_events(db: Database, bls_api_key: str | None = None) -> dict:
    """Sync market events from external sources.

    Returns dict with sync results per source.
    """
    results = {}

    # FOMC from Fed
    fomc_events = _fetch_fomc_events()
    for event in fomc_events:
        db.upsert("market_events", event, conflict_cols=["id"])
    results["fomc"] = len(fomc_events)
    logger.info("Synced %d FOMC events", len(fomc_events))

    # BLS events (if API key available)
    if bls_api_key:
        bls_events = _fetch_bls_events(bls_api_key)
        for event in bls_events:
            db.upsert("market_events", event, conflict_cols=["id"])
        results["bls"] = len(bls_events)
        logger.info("Synced %d BLS events", len(bls_events))
    else:
        results["bls"] = 0
        logger.info("BLS API key not configured, skipping")

    return results


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

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
