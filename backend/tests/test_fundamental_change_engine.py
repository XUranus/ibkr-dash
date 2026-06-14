"""Tests for FundamentalChangeEngine."""

from app.services.fundamental_change_engine import (
    FundamentalChangeEngine,
    FundamentalChangeResult,
    FUNDAMENTAL_STATUSES,
)
from app.services.investment_thesis import get_thesis


class TestFundamentalChangeEngine:
    def setup_method(self):
        self.engine = FundamentalChangeEngine()

    def test_empty_input(self):
        result = self.engine.evaluate()
        assert result.fundamental_status == "unknown"
        assert result.thesis_broken is False

    def test_revenue_slowdown(self):
        reports = [
            {"revenue": 100},
            {"revenue": 95},
            {"revenue": 90},
            {"revenue": 85},
        ]
        result = self.engine.evaluate(financial_reports=reports)
        assert result.revenue_growth_trend == "slowing"
        assert "revenue_growth_slowdown" in result.change_signals

    def test_revenue_acceleration(self):
        reports = [
            {"revenue": 100},
            {"revenue": 110},
            {"revenue": 120},
            {"revenue": 130},
        ]
        result = self.engine.evaluate(financial_reports=reports)
        assert result.revenue_growth_trend == "accelerating"

    def test_margin_compression(self):
        reports = [
            {"gross_margin": 60},
            {"gross_margin": 58},
            {"gross_margin": 55},
            {"gross_margin": 52},
        ]
        result = self.engine.evaluate(financial_reports=reports)
        assert result.margin_trend == "compressing"
        assert "margin_compression" in result.change_signals

    def test_cash_flow_deteriorating(self):
        reports = [
            {"free_cash_flow": 100},
            {"free_cash_flow": 80},
            {"free_cash_flow": -10},
        ]
        result = self.engine.evaluate(financial_reports=reports)
        # 2 consecutive declines → "deteriorating" (checked before "negative")
        assert result.cash_flow_trend == "deteriorating"
        assert "cash_flow_deterioration" in result.change_signals

    def test_cash_flow_negative_single_drop(self):
        # Only 2 data points (not enough for trend), last is negative
        reports = [
            {"operating_cash_flow": 50},
            {"operating_cash_flow": -5},
        ]
        result = self.engine.evaluate(financial_reports=reports)
        # <3 data points → data limitation, no trend computed
        assert any("现金流" in d for d in result.data_limitations)

    def test_guidance_cut(self):
        reports = [{"guidance": "公司下调了全年收入指引，预计低于市场预期"}]
        result = self.engine.evaluate(financial_reports=reports)
        assert result.guidance_change == "cut"
        assert "guidance_cut" in result.change_signals

    def test_guidance_raise(self):
        reports = [{"guidance": "公司上调了全年收入指引，超出市场预期"}]
        result = self.engine.evaluate(financial_reports=reports)
        assert result.guidance_change == "raised"

    def test_thesis_broken(self):
        reports = [
            {"revenue": 100, "gross_margin": 60, "guidance": "下调指引"},
            {"revenue": 95, "gross_margin": 55},
            {"revenue": 90, "gross_margin": 50},
        ]
        thesis = get_thesis("AMD")
        result = self.engine.evaluate(
            financial_reports=reports,
            investment_thesis=thesis,
        )
        # Should detect slowdown + compression + cut
        assert len(result.change_signals) > 0

    def test_status_green(self):
        reports = [
            {"revenue": 100, "gross_margin": 50},
            {"revenue": 110, "gross_margin": 52},
            {"revenue": 120, "gross_margin": 54},
        ]
        result = self.engine.evaluate(financial_reports=reports)
        # Positive signals should push toward green
        assert result.fundamental_status in ("green", "yellow")

    def test_to_dict(self):
        result = self.engine.evaluate()
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "fundamental_status" in d
        assert "thesis_broken" in d
