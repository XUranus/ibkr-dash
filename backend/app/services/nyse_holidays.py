"""NYSE holiday calculator — pure Python, no external dependencies.

Computes US stock market (NYSE/NASDAQ) holidays for any year using
the Meeus/Jones/Butcher algorithm for Easter and standard NYSE
observation rules for weekend holidays.

Reference: https://www.nyse.com/markets/hours-calendars
"""

from __future__ import annotations

from datetime import date, timedelta


def _easter_sunday(year: int) -> date:
    """Compute Easter Sunday for a given year using the Anonymous Gregorian algorithm.

    This is the Meeus/Jones/Butcher algorithm, valid for years in the
    Gregorian calendar (1583 onwards).
    """
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _observed(d: date) -> date:
    """Apply NYSE observation rules for holidays falling on weekends.

    - Saturday → observed on preceding Friday
    - Sunday  → observed on following Monday
    - Weekday → no change
    """
    if d.weekday() == 5:  # Saturday
        return d - timedelta(days=1)
    if d.weekday() == 6:  # Sunday
        return d + timedelta(days=1)
    return d


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Return the nth occurrence of a weekday in a month.

    weekday: 0=Mon, 1=Tue, ..., 6=Sun
    n: 1-based (1 = first, 2 = second, etc.)
    """
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    """Return the last occurrence of a weekday in a month."""
    # Start from end of month and go backwards
    if month == 12:
        last = date(year, 12, 31)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    offset = (last.weekday() - weekday) % 7
    return last - timedelta(days=offset)


def get_nyse_holidays(year: int) -> list[tuple[str, str]]:
    """Return all NYSE holidays for a given year.

    Returns list of (date_iso, name) tuples where date_iso is "YYYY-MM-DD"
    and name is the holiday name. Dates are the *observed* dates (i.e., if
    a holiday falls on Saturday, the Friday before is returned).

    Holidays included:
    1. New Year's Day
    2. Martin Luther King Jr. Day (3rd Monday of January)
    3. Presidents' Day (3rd Monday of February)
    4. Good Friday (Easter Sunday − 2 days)
    5. Memorial Day (Last Monday of May)
    6. Juneteenth (June 19)
    7. Independence Day (July 4)
    8. Labor Day (1st Monday of September)
    9. Thanksgiving Day (4th Thursday of November)
    10. Christmas Day (December 25)
    """
    holidays: list[tuple[str, str]] = []

    def _add(d: date, name: str) -> None:
        observed = _observed(d)
        holidays.append((observed.isoformat(), name))

    # 1. New Year's Day — Jan 1
    _add(date(year, 1, 1), "New Year's Day")

    # 2. MLK Day — 3rd Monday of January (always Monday, no observation needed)
    holidays.append((_nth_weekday(year, 1, 0, 3).isoformat(), "Martin Luther King Jr. Day"))

    # 3. Presidents' Day — 3rd Monday of February
    holidays.append((_nth_weekday(year, 2, 0, 3).isoformat(), "Presidents' Day"))

    # 4. Good Friday — Easter Sunday minus 2 days (always Friday)
    easter = _easter_sunday(year)
    holidays.append(((easter - timedelta(days=2)).isoformat(), "Good Friday"))

    # 5. Memorial Day — Last Monday of May
    holidays.append((_last_weekday(year, 5, 0).isoformat(), "Memorial Day"))

    # 6. Juneteenth — June 19
    _add(date(year, 6, 19), "Juneteenth National Independence Day")

    # 7. Independence Day — July 4
    _add(date(year, 7, 4), "Independence Day")

    # 8. Labor Day — 1st Monday of September
    holidays.append((_nth_weekday(year, 9, 0, 1).isoformat(), "Labor Day"))

    # 9. Thanksgiving — 4th Thursday of November
    holidays.append((_nth_weekday(year, 11, 3, 4).isoformat(), "Thanksgiving Day"))

    # 10. Christmas — Dec 25
    _add(date(year, 12, 25), "Christmas Day")

    # Sort by date
    holidays.sort(key=lambda x: x[0])
    return holidays


def get_nyse_holidays_range(start_year: int, end_year: int) -> list[tuple[str, str]]:
    """Return NYSE holidays for a range of years (inclusive)."""
    result: list[tuple[str, str]] = []
    for year in range(start_year, end_year + 1):
        result.extend(get_nyse_holidays(year))
    result.sort(key=lambda x: x[0])
    return result
