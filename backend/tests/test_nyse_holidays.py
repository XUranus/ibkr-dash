"""Tests for the NYSE holiday calculator."""

from __future__ import annotations

from datetime import date

from app.services.nyse_holidays import (
    _easter_sunday,
    _last_weekday,
    _nth_weekday,
    _observed,
    get_nyse_holidays,
    get_nyse_holidays_range,
)


class TestEasterSunday:
    """Verify Easter computation against known dates."""

    def test_easter_2025(self):
        assert _easter_sunday(2025) == date(2025, 4, 20)

    def test_easter_2026(self):
        assert _easter_sunday(2026) == date(2026, 4, 5)

    def test_easter_2027(self):
        assert _easter_sunday(2027) == date(2027, 3, 28)

    def test_easter_2028(self):
        assert _easter_sunday(2028) == date(2028, 4, 16)

    def test_easter_2024(self):
        assert _easter_sunday(2024) == date(2024, 3, 31)


class TestObserved:
    """Weekend observation rules."""

    def test_weekday_unchanged(self):
        # Wednesday
        assert _observed(date(2025, 1, 1)) == date(2025, 1, 1)

    def test_saturday_to_friday(self):
        # July 4, 2026 is Saturday → observed Friday July 3
        assert _observed(date(2026, 7, 4)) == date(2026, 7, 3)

    def test_sunday_to_monday(self):
        # July 4, 2027 is Sunday → observed Monday July 5
        assert _observed(date(2027, 7, 4)) == date(2027, 7, 5)

    def test_friday_unchanged(self):
        assert _observed(date(2025, 7, 4)) == date(2025, 7, 4)


class TestNthWeekday:
    """nth weekday of a month."""

    def test_first_monday(self):
        # First Monday of Sep 2025 = Sep 1
        assert _nth_weekday(2025, 9, 0, 1) == date(2025, 9, 1)

    def test_third_monday(self):
        # Third Monday of Jan 2025 = Jan 20
        assert _nth_weekday(2025, 1, 0, 3) == date(2025, 1, 20)

    def test_fourth_thursday(self):
        # Fourth Thursday of Nov 2025 = Nov 27
        assert _nth_weekday(2025, 11, 3, 4) == date(2025, 11, 27)


class TestLastWeekday:
    """Last weekday of a month."""

    def test_last_monday_may_2025(self):
        assert _last_weekday(2025, 5, 0) == date(2025, 5, 26)

    def test_last_monday_may_2026(self):
        assert _last_weekday(2026, 5, 0) == date(2026, 5, 25)

    def test_last_monday_may_2027(self):
        assert _last_weekday(2027, 5, 0) == date(2027, 5, 31)


class TestGetNyseHolidays:
    """Full holiday list for a given year."""

    def test_2025_count(self):
        holidays = get_nyse_holidays(2025)
        assert len(holidays) == 10

    def test_2025_dates(self):
        holidays = get_nyse_holidays(2025)
        dates = [d for d, _ in holidays]
        assert "2025-01-01" in dates  # New Year
        assert "2025-01-20" in dates  # MLK
        assert "2025-02-17" in dates  # Presidents
        assert "2025-04-18" in dates  # Good Friday (Easter Apr 20 - 2)
        assert "2025-05-26" in dates  # Memorial
        assert "2025-06-19" in dates  # Juneteenth
        assert "2025-07-04" in dates  # Independence
        assert "2025-09-01" in dates  # Labor
        assert "2025-11-27" in dates  # Thanksgiving
        assert "2025-12-25" in dates  # Christmas

    def test_2026_independence_day_observed(self):
        """July 4, 2026 is Saturday → observed Friday July 3."""
        holidays = get_nyse_holidays(2026)
        dates = [d for d, _ in holidays]
        assert "2026-07-03" in dates
        assert "2026-07-04" not in dates

    def test_2027_independence_day_observed(self):
        """July 4, 2027 is Sunday → observed Monday July 5."""
        holidays = get_nyse_holidays(2027)
        dates = [d for d, _ in holidays]
        assert "2027-07-05" in dates
        assert "2027-07-04" not in dates

    def test_2027_christmas_observed(self):
        """Dec 25, 2027 is Saturday → observed Friday Dec 24."""
        holidays = get_nyse_holidays(2027)
        dates = [d for d, _ in holidays]
        assert "2027-12-24" in dates
        assert "2027-12-25" not in dates

    def test_2027_juneteenth_observed(self):
        """June 19, 2027 is Saturday → observed Friday June 18."""
        holidays = get_nyse_holidays(2027)
        dates = [d for d, _ in holidays]
        assert "2027-06-18" in dates
        assert "2027-06-19" not in dates

    def test_sorted_by_date(self):
        holidays = get_nyse_holidays(2025)
        dates = [d for d, _ in holidays]
        assert dates == sorted(dates)

    def test_all_weekdays_are_trading_days(self):
        """No holiday should fall on a Saturday or Sunday."""
        for year in range(2025, 2031):
            for dt_str, _ in get_nyse_holidays(year):
                dt = date.fromisoformat(dt_str)
                assert dt.weekday() < 5, f"{dt_str} ({dt.strftime('%A')}) is not a weekday"


class TestGetNyseHolidaysRange:
    """Multi-year range."""

    def test_range_count(self):
        holidays = get_nyse_holidays_range(2025, 2027)
        assert len(holidays) == 30  # 10 per year

    def test_sorted(self):
        holidays = get_nyse_holidays_range(2025, 2027)
        dates = [d for d, _ in holidays]
        assert dates == sorted(dates)

    def test_single_year(self):
        holidays = get_nyse_holidays_range(2026, 2026)
        assert len(holidays) == 10
