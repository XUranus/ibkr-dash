"""Date parsing and formatting helpers."""

from datetime import date, datetime, timedelta, timezone


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# Convenience alias used by several modules.
now_iso = utc_now_iso


def parse_date(value: str | None) -> date | None:
    """Parse an ISO-format date string, returning None for empty/missing values."""
    if not value:
        return None
    return date.fromisoformat(value)


def get_default_start_date(end_date: date, days: int = 90) -> date:
    """Calculate a default start date by subtracting days from the end date."""
    return end_date - timedelta(days=days - 1)
