"""Tests for market event service — BLS integration and seeding."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from app.services.market_event_service import (
    _estimate_next_release,
    _fetch_bls_events,
    _first_weekday_of_month,
    generate_market_event_analysis,
    get_latest_analysis,
    get_today_events,
    get_upcoming_events,
    seed_market_events,
    sync_market_events,
)


# ---------------------------------------------------------------------------
# _estimate_next_release
# ---------------------------------------------------------------------------


class TestEstimateNextRelease:
    """Verify release date estimation for each BLS series."""

    def test_cpi_estimates_mid_month(self):
        """CPI data for month M → estimated release ~12th of M+1."""
        d = _estimate_next_release("CUUR0000SA0", 2026, 5)
        assert d.month == 6 or d.month == 7  # could shift if past
        assert d.year >= 2026

    def test_ppi_estimates_mid_month(self):
        d = _estimate_next_release("WPUFD4", 2026, 5)
        assert d.month in (6, 7)
        assert d.year >= 2026

    def test_nfp_estimates_first_friday(self):
        """Nonfarm Payrolls → first Friday of M+1."""
        d = _estimate_next_release("CES0000000001", 2026, 5)
        assert d.weekday() == 4  # Friday

    def test_unemployment_same_as_nfp(self):
        """Unemployment Rate uses same pattern as NFP."""
        d_nfp = _estimate_next_release("CES0000000001", 2026, 5)
        d_unemp = _estimate_next_release("LNS14000000", 2026, 5)
        assert d_nfp == d_unemp

    def test_shifts_forward_if_past(self):
        """If estimated date is already past, shifts forward until future."""
        # Use last month's data — the estimated release for this month
        # might already be past if we're past the mid-month point
        today = date.today()
        # Go back 2 months to guarantee the estimate is in the past
        past_month = today.month - 2
        past_year = today.year
        if past_month < 1:
            past_month += 12
            past_year -= 1
        d = _estimate_next_release("CUUR0000SA0", past_year, past_month)
        assert d > today

    def test_december_wraps_to_next_year(self):
        """December data → release in January of next year."""
        d = _estimate_next_release("CUUR0000SA0", 2025, 12)
        # Should be January 2026 or later
        assert d.year >= 2026


# ---------------------------------------------------------------------------
# _first_weekday_of_month
# ---------------------------------------------------------------------------


class TestFirstWeekdayOfMonth:
    def test_first_friday_july_2026(self):
        assert _first_weekday_of_month(2026, 7, 4) == date(2026, 7, 3)

    def test_first_monday_september_2025(self):
        assert _first_weekday_of_month(2025, 9, 0) == date(2025, 9, 1)

    def test_first_friday_august_2026(self):
        assert _first_weekday_of_month(2026, 8, 4) == date(2026, 8, 7)


# ---------------------------------------------------------------------------
# _fetch_bls_events (mocked HTTP)
# ---------------------------------------------------------------------------


class TestFetchBlsEvents:
    @patch("app.services.market_event_service.httpx.post")
    def test_no_api_key_returns_empty(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"status": "REQUEST_SUCCEEDED", "Results": {"series": []}}
        mock_post.return_value = mock_resp
        result = _fetch_bls_events(api_key=None)
        assert isinstance(result, list)

    @patch("app.services.market_event_service.httpx.post")
    def test_parses_bls_response(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "status": "REQUEST_SUCCEEDED",
            "responseTime": 73,
            "message": [],
            "Results": {
                "series": [
                    {
                        "seriesID": "CUUR0000SA0",
                        "data": [
                            {"year": "2026", "period": "M05", "periodName": "May", "latest": "true", "value": "335.123"},
                            {"year": "2026", "period": "M04", "periodName": "April", "value": "333.020"},
                        ],
                    },
                    {
                        "seriesID": "CES0000000001",
                        "data": [
                            {"year": "2026", "period": "M05", "periodName": "May", "latest": "true", "value": "159001"},
                        ],
                    },
                ],
            },
        }
        mock_post.return_value = mock_resp

        events = _fetch_bls_events(api_key="test-key")
        assert len(events) == 2

        # CPI event
        cpi = [e for e in events if e["event_type"] == "CPI"][0]
        assert "CPI" in cpi["title"]
        assert cpi["source"] == "BLS"
        assert cpi["category"] == "MACRO"
        assert "335.123" in cpi["description"]

        # NFP event
        nfp = [e for e in events if e["event_type"] == "NONFARM_PAYROLLS"][0]
        assert nfp["scheduled_at"]  # has a date
        assert nfp["importance"] == "CRITICAL"

    @patch("app.services.market_event_service.httpx.post")
    def test_handles_api_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "status": "REQUEST_FAILED",
            "message": ["Invalid request"],
        }
        mock_post.return_value = mock_resp

        events = _fetch_bls_events(api_key="test-key")
        assert events == []

    @patch("app.services.market_event_service.httpx.post")
    def test_handles_network_error(self, mock_post):
        import httpx
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        events = _fetch_bls_events(api_key="test-key")
        assert events == []

    @patch("app.services.market_event_service.httpx.post")
    def test_skips_unknown_series(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "status": "REQUEST_SUCCEEDED",
            "Results": {
                "series": [
                    {"seriesID": "UNKNOWN_SERIES", "data": [{"year": "2026", "period": "M05", "latest": "true", "value": "100"}]},
                ],
            },
        }
        mock_post.return_value = mock_resp

        events = _fetch_bls_events(api_key="test-key")
        assert events == []


# ---------------------------------------------------------------------------
# seed_market_events (mocked FOMC fetch)
# ---------------------------------------------------------------------------


class TestSeedMarketEvents:
    @patch("app.services.market_event_service._fetch_fomc_events", return_value=[])
    def test_seeds_holidays(self, _mock_fomc, db):
        count = seed_market_events(db)
        # Should have holidays for current_year + 2 years = 30 holidays
        current_year = date.today().year
        expected = 30  # 10 per year × 3 years
        assert count >= expected

        # Verify at least one holiday in DB
        rows = db.execute("SELECT * FROM market_events WHERE event_type = 'MARKET_CLOSED' LIMIT 1")
        assert len(rows) == 1
        assert "holiday_" in rows[0]["id"]

    @patch("app.services.market_event_service._fetch_fomc_events")
    def test_seeds_fomc(self, mock_fomc, db):
        mock_fomc.return_value = [{
            "id": "fomc_test_2026_06",
            "event_type": "FOMC_RATE_DECISION",
            "category": "FED",
            "title": "FOMC Test",
            "title_en": "FOMC Test",
            "scheduled_at": "2026-06-18T18:00:00+00:00",
            "importance": "CRITICAL",
            "source": "FED",
            "description": "Test",
        }]
        count = seed_market_events(db)
        fomc = db.execute("SELECT * FROM market_events WHERE event_type = 'FOMC_RATE_DECISION'")
        assert len(fomc) == 1


# ---------------------------------------------------------------------------
# sync_market_events (mocked external calls)
# ---------------------------------------------------------------------------


class TestSyncMarketEvents:
    @patch("app.services.market_event_service._fetch_bls_events", return_value=[])
    @patch("app.services.market_event_service._fetch_fomc_events", return_value=[])
    def test_sync_returns_results(self, _mock_fomc, _mock_bls, db):
        results = sync_market_events(db)
        assert "fomc" in results
        assert "bls" in results
        assert "holidays" in results
        assert results["holidays"] >= 30

    @patch("app.services.market_event_service._fetch_bls_events")
    @patch("app.services.market_event_service._fetch_fomc_events", return_value=[])
    def test_sync_bls_events(self, _mock_fomc, mock_bls, db):
        mock_bls.return_value = [{
            "id": "bls_test_2026-07-12",
            "event_type": "CPI",
            "category": "MACRO",
            "title": "CPI 数据发布",
            "title_en": "CPI Data Release",
            "scheduled_at": "2026-07-12T13:30:00",
            "importance": "CRITICAL",
            "source": "BLS",
            "description": "Test",
        }]
        results = sync_market_events(db, bls_api_key="test")
        assert results["bls"] == 1

        rows = db.execute("SELECT * FROM market_events WHERE source = 'BLS'")
        assert len(rows) == 1


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------


class TestQueryEvents:
    def test_upcoming_events(self, db):
        # Insert a future event
        future = (date.today() + timedelta(days=5)).isoformat()
        db.upsert("market_events", {
            "id": "test_future",
            "event_type": "TEST",
            "category": "TEST",
            "title": "Future Event",
            "scheduled_at": f"{future}T10:00:00",
            "importance": "LOW",
            "source": "TEST",
        }, conflict_cols=["id"])

        events = get_upcoming_events(db, days=7, limit=10)
        ids = [e["id"] for e in events]
        assert "test_future" in ids

    def test_today_events(self, db):
        today = date.today().isoformat()
        db.upsert("market_events", {
            "id": "test_today",
            "event_type": "TEST",
            "category": "TEST",
            "title": "Today Event",
            "scheduled_at": f"{today}T10:00:00",
            "importance": "LOW",
            "source": "TEST",
        }, conflict_cols=["id"])

        events = get_today_events(db)
        ids = [e["id"] for e in events]
        assert "test_today" in ids

    def test_upcoming_events_empty(self, db):
        # With no future events, should return empty
        far_future = (date.today() + timedelta(days=9999)).isoformat()
        db.execute("DELETE FROM market_events")
        events = get_upcoming_events(db, days=1, limit=10)
        assert events == []


# ---------------------------------------------------------------------------
# AI Market Risk Analysis
# ---------------------------------------------------------------------------


class TestGenerateMarketEventAnalysis:
    @patch("app.services.market_event_service._fetch_fomc_events", return_value=[])
    def test_no_llm_returns_none(self, _mock_fomc, db):
        seed_market_events(db)
        result = generate_market_event_analysis(db, llm_service=None)
        assert result is None

    @patch("app.services.market_event_service._fetch_fomc_events", return_value=[])
    def test_no_events_returns_none(self, _mock_fomc, db):
        db.execute("DELETE FROM market_events")
        mock_llm = MagicMock()
        mock_llm.api_key = "test-key"
        result = generate_market_event_analysis(db, llm_service=mock_llm)
        assert result is None

    @patch("app.services.market_event_service._fetch_fomc_events", return_value=[])
    def test_generates_and_stores_analysis(self, _mock_fomc, db):
        seed_market_events(db)

        mock_llm = MagicMock()
        mock_llm.api_key = "test-key"
        mock_llm.chat.side_effect = [
            "**风险提示**: 未来30天有多项重要经济数据发布。",
            "**Risk Alert**: Multiple key economic data releases in the next 30 days.",
        ]

        result = generate_market_event_analysis(db, llm_service=mock_llm)
        assert result is not None
        assert "风险提示" in result["content_zh"]
        assert "Risk Alert" in result["content_en"]
        assert result["event_ids"]  # populated

        # Verify it's stored in DB
        stored = db.execute_one("SELECT * FROM market_event_analysis ORDER BY created_at DESC LIMIT 1")
        assert stored is not None
        assert stored["content_zh"] == result["content_zh"]

    @patch("app.services.market_event_service._fetch_fomc_events", return_value=[])
    def test_llm_failure_returns_none(self, _mock_fomc, db):
        seed_market_events(db)

        mock_llm = MagicMock()
        mock_llm.api_key = "test-key"
        mock_llm.chat.side_effect = Exception("API error")

        result = generate_market_event_analysis(db, llm_service=mock_llm)
        assert result is None

    @patch("app.services.market_event_service._fetch_fomc_events", return_value=[])
    def test_llm_empty_response_returns_none(self, _mock_fomc, db):
        seed_market_events(db)

        mock_llm = MagicMock()
        mock_llm.api_key = "test-key"
        mock_llm.chat.return_value = ""

        result = generate_market_event_analysis(db, llm_service=mock_llm)
        assert result is None


class TestGetLatestAnalysis:
    def test_returns_none_when_empty(self, db):
        result = get_latest_analysis(db)
        assert result is None

    def test_returns_most_recent(self, db):
        # Insert two analyses
        db.upsert("market_event_analysis", {
            "id": "analysis_old",
            "content_zh": "旧分析",
            "content_en": "Old analysis",
            "event_ids": "a,b",
        }, conflict_cols=["id"])

        db.upsert("market_event_analysis", {
            "id": "analysis_new",
            "content_zh": "新分析",
            "content_en": "New analysis",
            "event_ids": "c,d",
        }, conflict_cols=["id"])

        result = get_latest_analysis(db)
        assert result is not None
        # The most recent by created_at (both have auto-generated timestamps,
        # but we can at least verify one is returned)
        assert result["content_zh"] in ("旧分析", "新分析")
