"""Tests for PortfolioWatchtowerService with SQLite."""

from __future__ import annotations

from datetime import date, timedelta

from app.domains.portfolio_manager.watchtower.repository import PortfolioWatchtowerRepository
from app.domains.portfolio_manager.watchtower.scanner import PortfolioWatchtowerScanner, WatchtowerPriceBar
from app.domains.portfolio_manager.watchtower.service import PortfolioWatchtowerService
from app.schemas.positions import PositionItem, PositionListResponse
from app.utils.pagination import build_pagination_info
from tests.pm_helpers import make_test_db


class FakeConstitutionService:
    def get_current(self):
        class C:
            constitution_version = "v1"
            def model_dump(self):
                return {"id": "default", "constitution_version": "v1", "primary_theme": "AI", "primary_theme_buckets": ["semi"], "target_account_value_usd": 1500000, "target_date": "2035-12-31"}
        return C()


class FakeUniverseService:
    def __init__(self):
        self.items = [
            _universe("AMD", "holding", enabled=True),
            _universe("AVGO", "watchlist", enabled=True),
            _universe("TSM", "candidate", enabled=False),
            _universe("FAKE", "excluded", enabled=True),
        ]
    def list_symbols(self, *, universe_type=None, enabled=None, **_kw):
        r = self.items
        if universe_type: r = [i for i in r if i.universe_type == universe_type]
        if enabled is not None: r = [i for i in r if i.enabled == enabled]
        return r


class FakePositionService:
    def list_positions(self, **_kw):
        return PositionListResponse(items=[PositionItem(account_id="U1", report_date="2026-06-15", symbol="AMD.US", quantity=10, position_value=15000, unrealized_pnl_percent=20)], pagination=build_pagination_info(1, 1000, 1))


class FakeScanner(PortfolioWatchtowerScanner):
    def fetch_price_bars(self, item, *, run_date=None):
        if item.symbol == "AVGO":
            return [], ["price_history_missing:AVGO"]
        start = date(2026, 1, 1)
        closes = [100 + i for i in range(55)] + [160, 150, 140, 130, 120, 110, 100]
        return [WatchtowerPriceBar(symbol=item.symbol, report_date=start + timedelta(days=i), close_price=c) for i, c in enumerate(closes)], []


def _universe(symbol, universe_type, *, enabled):
    from app.domains.portfolio_manager.universe.schemas import UniverseSymbol
    return UniverseSymbol(id=f"universe:{symbol}", symbol=symbol, display_symbol=symbol, name=symbol, universe_type=universe_type, theme_tags=["AI"], ai_theme_role="semiconductor", priority="high", enabled=enabled, scan_frequency="daily", decision_frequency="event_driven", max_llm_runs_per_week=3, source="manual", notes="", excluded_reason=None, created_at="2026-01-01T00:00:00+00:00", updated_at="2026-01-01T00:00:00+00:00")


def make_service():
    db = make_test_db()
    return PortfolioWatchtowerService(
        repository=PortfolioWatchtowerRepository(db),
        universe_service=FakeUniverseService(),
        constitution_service=FakeConstitutionService(),
        position_service=FakePositionService(),
        scanner=FakeScanner(),
    )


def test_run_watchtower_creates_run_and_items_with_summary_and_snapshot():
    service = make_service()
    detail = service.run_watchtower(run_date="2026-06-15", run_type="manual")
    assert detail.status == "partial_success"
    assert len(detail.items) == 2
    assert {item.symbol for item in detail.items} == {"AMD", "AVGO"}
    assert detail.summary["decision_required"] == 1
    assert detail.summary["normal"] == 1
    assert detail.top_attention_symbols == ["AMD"]
    assert detail.items[0].scan_snapshot
    assert any("AVGO:price_history_missing" in item for item in detail.data_limitations)


def test_excluded_and_disabled_are_not_scanned():
    service = make_service()
    detail = service.run_watchtower(run_date="2026-06-15", run_type="manual")
    assert "TSM" not in {item.symbol for item in detail.items}
    assert "FAKE" not in {item.symbol for item in detail.items}


def test_repository_queries_run_detail_and_symbol_history():
    service = make_service()
    detail = service.run_watchtower(run_date="2026-06-15", run_type="manual")
    loaded = service.get_run_detail(detail.id)
    history = service.list_symbol_history("AMD.US")
    assert loaded.id == detail.id
    assert loaded.items
    assert history[0].symbol == "AMD"
