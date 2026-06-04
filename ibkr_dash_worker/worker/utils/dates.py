"""Date parsing helpers for IBKR Flex CSV date/datetime formats."""

from datetime import UTC, date, datetime


DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y%m%d",
    "%m/%d/%Y",
)

DATETIME_FORMATS: tuple[str, ...] = (
    "%Y%m%d;%H%M%S",
    "%Y%m%d;%H%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d,%H:%M:%S",
    "%Y-%m-%d,%H:%M",
    "%Y/%m/%d,%H:%M:%S",
    "%Y/%m/%d,%H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
)


def parse_date_value(value: str | None) -> date | None:
    """Parse an IBKR date string into a date object."""
    if value is None:
        return None

    cleaned = value.strip()
    if not cleaned:
        return None

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(cleaned).date()
    except ValueError:
        return None


def parse_datetime_value(value: str | None) -> datetime | None:
    """Parse an IBKR datetime string into a datetime object."""
    if value is None:
        return None

    cleaned = value.strip()
    if not cleaned:
        return None

    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def to_iso_date(value: str | None) -> str | None:
    """Convert an IBKR date string to ISO format (YYYY-MM-DD)."""
    parsed = parse_date_value(value)
    return parsed.isoformat() if parsed else None


def to_iso_datetime(value: str | None) -> str | None:
    """Convert an IBKR datetime string to ISO format."""
    parsed = parse_datetime_value(value)
    return parsed.isoformat() if parsed else None


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO string."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
