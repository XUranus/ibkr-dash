"""Market event service: fetch, seed, and query market events.

Data sources:
1. Federal Reserve FOMC calendar (scraped from federalreserve.gov)
2. BLS release dates (API v2, estimated from latest data period)
3. NYSE market holidays (algorithmically computed, no hardcoded list)
"""

from __future__ import annotations

import calendar
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import httpx

from app.core.database import Database
from app.services.nyse_holidays import get_nyse_holidays_range

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 15.0
HTTP_HEADERS = {
    "User-Agent": "ibkr-dash/1.0 (market-event-calendar)",
    "Accept": "text/html,application/json,*/*;q=0.8",
}


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
        resp = httpx.get(FOMC_CALENDAR_URL, headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT, follow_redirects=False)
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
# BLS provider (BLS API v2 — estimates next release dates from data period)
# ---------------------------------------------------------------------------

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# Series ID → (display name, event_type, importance)
BLS_SERIES: dict[str, tuple[str, str, str]] = {
    "CUUR0000SA0": ("CPI", "CPI", "CRITICAL"),
    "WPUFD4": ("PPI", "PPI", "HIGH"),
    "CES0000000001": ("Nonfarm Payrolls", "NONFARM_PAYROLLS", "CRITICAL"),
    "LNS14000000": ("Unemployment Rate", "UNEMPLOYMENT_RATE", "CRITICAL"),
}

# Estimated release day patterns for each series.
# BLS releases data for month M around these dates of month M+1.
# "day_range" = (earliest_day, latest_day) in the following month.
# "weekday" = if set, the specific weekday (0=Mon..6=Sun) — used for
#             Employment Situation which is always the first Friday.
_RELEASE_PATTERNS: dict[str, dict[str, Any]] = {
    "CUUR0000SA0": {"day_range": (10, 14)},   # CPI: ~10th-14th
    "WPUFD4":      {"day_range": (11, 15)},   # PPI: ~11th-15th
    "CES0000000001": {"first_weekday": 4},     # Employment Situation: first Friday
    "LNS14000000": {"first_weekday": 4},       # Unemployment: same report as NFP
}


def _first_weekday_of_month(year: int, month: int, weekday: int) -> date:
    """Return the first occurrence of a weekday in a given month.

    weekday: 0=Mon, 1=Tue, ..., 4=Fri, ..., 6=Sun
    """
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset)


def _estimate_next_release(series_id: str, data_year: int, data_month: int) -> date:
    """Estimate the next release date for a BLS series.

    BLS releases data for month M in month M+1.  We take the latest
    data period (data_year, data_month) and compute an estimated date
    in the following month using known release patterns.

    If the estimated date is in the past, we keep shifting forward one
    month at a time until we find a future date.
    """
    pattern = _RELEASE_PATTERNS.get(series_id, {})
    today = date.today()

    # Start from the month following the data period
    next_month = data_month + 1
    next_year = data_year
    if next_month > 12:
        next_month = 1
        next_year += 1

    # Loop until we find a future date (max 120 iterations as safety)
    for _ in range(120):
        if "first_weekday" in pattern:
            estimated = _first_weekday_of_month(next_year, next_month, pattern["first_weekday"])
        elif "day_range" in pattern:
            day_lo, day_hi = pattern["day_range"]
            mid_day = (day_lo + day_hi) // 2
            max_day = calendar.monthrange(next_year, next_month)[1]
            estimated = date(next_year, next_month, min(mid_day, max_day))
        else:
            max_day = calendar.monthrange(next_year, next_month)[1]
            estimated = date(next_year, next_month, min(15, max_day))

        if estimated > today:
            return estimated

        # Shift forward one month
        next_month += 1
        if next_month > 12:
            next_month = 1
            next_year += 1

    # Fallback (should never reach here with reasonable input)
    return estimated


def _fetch_bls_events(api_key: str | None = None) -> list[dict]:
    """Fetch latest BLS data via API v2 and estimate next release dates.

    The BLS API v2 returns time series data (not release calendars).
    We fetch the latest data point for each series, infer the data period,
    and estimate when the next release will occur based on known patterns.

    Works without API key (25 req/day limit). With key: 500 req/day.
    """
    events: list[dict] = []

    # Fetch all series in a single POST (up to 50 per request)
    series_ids = list(BLS_SERIES.keys())
    payload: dict[str, Any] = {
        "seriesid": series_ids,
        "startyear": str(date.today().year - 1),
        "endyear": str(date.today().year),
    }
    if api_key:
        payload["registrationkey"] = api_key

    try:
        resp = httpx.post(
            BLS_API_URL,
            json=payload,
            headers={"Content-type": "application/json"},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.warning("BLS API HTTP error %s: %s", exc.response.status_code, exc)
        return events
    except httpx.RequestError as exc:
        logger.warning("BLS API request failed: %s", exc)
        return events
    except Exception as exc:
        logger.warning("Unexpected error fetching BLS data: %s", exc)
        return events

    if data.get("status") != "REQUEST_SUCCEEDED":
        logger.warning("BLS API returned non-success status: %s", data.get("status"))
        msg = data.get("message", [])
        if msg:
            logger.warning("BLS API message: %s", msg)
        return events

    # Parse each series
    for series in data.get("Results", {}).get("series", []):
        series_id = series.get("seriesID", "")
        if series_id not in BLS_SERIES:
            continue

        name, event_type, importance = BLS_SERIES[series_id]
        rows = series.get("data", [])

        # Find the latest data point (look for "latest" flag or highest year+period)
        latest_row = None
        for row in rows:
            if row.get("latest") == "true":
                latest_row = row
                break
        if latest_row is None and rows:
            # Fallback: sort by year and period
            def _sort_key(r: dict) -> tuple[int, int]:
                yr = int(r.get("year", 0))
                per = int(r.get("period", "M0")[1:]) if r.get("period", "").startswith("M") else 0
                return (yr, per)
            rows_sorted = sorted(rows, key=_sort_key, reverse=True)
            latest_row = rows_sorted[0]

        if not latest_row:
            logger.info("BLS series %s: no data points found", series_id)
            continue

        data_year = int(latest_row["year"])
        period = latest_row.get("period", "")
        data_month = int(period[1:]) if period.startswith("M") else 0
        value = latest_row.get("value", "N/A")

        if data_month < 1 or data_month > 12:
            logger.warning("BLS series %s: invalid period %s", series_id, period)
            continue

        # Estimate next release date
        estimated_date = _estimate_next_release(series_id, data_year, data_month)
        period_name = latest_row.get("periodName", f"Month {data_month}")

        events.append({
            "id": f"bls_{series_id}_{estimated_date.isoformat()}",
            "event_type": event_type,
            "category": "MACRO",
            "title": f"{name} {data_year}年{period_name}数据发布",
            "title_en": f"{name} {period_name} {data_year} Data Release",
            "scheduled_at": f"{estimated_date.isoformat()}T13:30:00",  # BLS typically releases at 8:30 AM ET
            "importance": importance,
            "source": "BLS",
            "description": f"最新数据: {period_name} {data_year} = {value}（发布日期为预估）",
        })

        logger.info("BLS %s: latest period %s-%s (value=%s), next release est. %s",
                     series_id, data_year, period_name, value, estimated_date)

    if events:
        logger.info("Generated %d BLS release events from API data", len(events))
    else:
        logger.info("No BLS events generated (no data or all series empty)")

    return events


# ---------------------------------------------------------------------------
# Seed and sync
# ---------------------------------------------------------------------------

def _upsert_holidays(db: Database, holidays: list[tuple[str, str]]) -> int:
    """Upsert NYSE holidays into the database. Returns count."""
    for dt, name in holidays:
        event_id = f"holiday_{dt}"
        db.upsert("market_events", {
            "id": event_id,
            "event_type": "MARKET_CLOSED",
            "category": "MARKET",
            "title": f"休市: {name}",
            "title_en": f"Market Closed: {name}",
            "scheduled_at": f"{dt}T09:30:00",
            "importance": "MEDIUM",
            "source": "ALGORITHM",
            "description": name,
        }, conflict_cols=["id"])
    return len(holidays)


def seed_market_events(db: Database) -> int:
    """Seed market events: NYSE holidays (dynamic) + FOMC from Fed.

    Holidays are computed algorithmically for the current year and the
    next two years — no hardcoded list.
    """
    count = 0
    current_year = date.today().year

    # NYSE holidays — computed dynamically
    holidays = get_nyse_holidays_range(current_year, current_year + 2)
    count += _upsert_holidays(db, holidays)

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

    # BLS events (estimated release dates from API v2)
    bls_events = _fetch_bls_events(bls_api_key)
    for event in bls_events:
        db.upsert("market_events", event, conflict_cols=["id"])
    results["bls"] = len(bls_events)
    logger.info("Synced %d BLS events", len(bls_events))

    # Re-seed holidays for current + 2 years (in case year rolled over)
    current_year = date.today().year
    holidays = get_nyse_holidays_range(current_year, current_year + 2)
    results["holidays"] = _upsert_holidays(db, holidays)
    logger.info("Synced %d NYSE holidays", len(holidays))

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


# ---------------------------------------------------------------------------
# AI Market Risk Analysis
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_ZH = (
    "你是一位金融市场风险分析师。根据即将到来的市场事件，分析未来30天的交易风险。"
    "要求：使用Markdown格式，200字以内，重点列出关键风险和需要注意的日期。"
    "使用**加粗**标注最重要的风险点。"
)

_SYSTEM_PROMPT_EN = (
    "You are a financial market risk analyst. Based on upcoming market events, "
    "analyze trading risks for the next 30 days. "
    "Requirements: Use Markdown format, under 200 words, highlight key risks and dates to watch. "
    "Use **bold** for the most important risk points."
)

_USER_PROMPT_TEMPLATE_ZH = (
    "以下是未来{days}天的市场重点事件：\n\n{event_list}\n\n"
    "请分析这些事件对交易的风险影响，200字以内的中文Markdown。"
)

_USER_PROMPT_TEMPLATE_EN = (
    "Here are the key market events for the next {days} days:\n\n{event_list}\n\n"
    "Analyze the trading risk implications of these events. "
    "Respond in English, under 200 words, Markdown format."
)


def _format_events_for_prompt(events: list[dict], is_zh: bool) -> str:
    """Format events into a readable list for the LLM prompt."""
    lines = []
    for e in events:
        dt = e.get("scheduled_at", "")[:10]
        title = e.get("title", "") if is_zh else (e.get("title_en") or e.get("title", ""))
        importance = e.get("importance", "MEDIUM")
        category = e.get("category", "")
        lines.append(f"- **{dt}** | {title} | {importance} | {category}")
    return "\n".join(lines)


def generate_market_event_analysis(
    db: Any,
    llm_service: Any,
    days: int = 30,
) -> dict | None:
    """Generate a bilingual market risk analysis using LLM.

    Fetches upcoming events, asks LLM to summarize risks in ZH and EN,
    and stores the result in the ``market_event_analysis`` table.

    Returns the saved document dict, or None if LLM is unavailable or fails.
    """
    if not llm_service or not getattr(llm_service, "api_key", None):
        logger.info("LLM not configured, skipping market event analysis")
        return None

    events = get_upcoming_events(db, days=days, limit=50)
    if not events:
        logger.info("No upcoming events, skipping market event analysis")
        return None

    event_ids = ",".join(e.get("id", "") for e in events)

    # Generate Chinese analysis
    event_list_zh = _format_events_for_prompt(events, is_zh=True)
    messages_zh = [
        {"role": "system", "content": _SYSTEM_PROMPT_ZH},
        {"role": "user", "content": _USER_PROMPT_TEMPLATE_ZH.format(days=days, event_list=event_list_zh)},
    ]

    # Generate English analysis
    event_list_en = _format_events_for_prompt(events, is_zh=False)
    messages_en = [
        {"role": "system", "content": _SYSTEM_PROMPT_EN},
        {"role": "user", "content": _USER_PROMPT_TEMPLATE_EN.format(days=days, event_list=event_list_en)},
    ]

    try:
        content_zh = llm_service.chat(messages_zh, max_tokens=1024, timeout=60)
        content_en = llm_service.chat(messages_en, max_tokens=1024, timeout=60)
    except Exception as exc:
        logger.warning("Failed to generate market event analysis: %s", exc)
        return None

    if not content_zh or not content_en:
        logger.warning("LLM returned empty analysis")
        return None

    analysis_id = f"analysis_{uuid4().hex[:12]}"
    doc = {
        "id": analysis_id,
        "content_zh": content_zh.strip(),
        "content_en": content_en.strip(),
        "event_ids": event_ids,
    }
    db.upsert("market_event_analysis", doc, conflict_cols=["id"])

    logger.info("Generated market event analysis (%d events, zh=%d chars, en=%d chars)",
                len(events), len(content_zh), len(content_en))
    return doc


def get_latest_analysis(db: Any) -> dict | None:
    """Return the most recent market event analysis, or None."""
    return db.execute_one(
        "SELECT * FROM market_event_analysis ORDER BY created_at DESC LIMIT 1"
    )
