"""Number and string parsing helpers for IBKR Flex CSV data."""

from __future__ import annotations


def clean_string(value: object) -> str | None:
    """Strip whitespace from a value; return None for empty/blank strings."""
    if value is None:
        return None

    cleaned = str(value).strip()
    return cleaned or None


def to_float(value: object) -> float | None:
    """Parse a value into a float, handling IBKR formatting.

    Handles comma-separated thousands, dollar signs, percent signs,
    and parenthesized negative numbers like (1,234.56).
    """
    cleaned = clean_string(value)
    if cleaned is None:
        return None

    negative = False
    normalized = cleaned.replace(",", "").replace("$", "").replace("%", "")
    if normalized.startswith("(") and normalized.endswith(")"):
        negative = True
        normalized = normalized[1:-1]

    try:
        parsed = float(normalized)
    except ValueError:
        return None

    return -parsed if negative else parsed


def to_bool(value: object) -> bool | None:
    """Parse a value into a boolean."""
    cleaned = clean_string(value)
    if cleaned is None:
        return None

    lowered = cleaned.lower()
    if lowered in {"true", "1", "yes", "y"}:
        return True
    if lowered in {"false", "0", "no", "n"}:
        return False
    return None
