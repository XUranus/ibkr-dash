"""Tests for RiskRewardEngine."""

from app.services.risk_reward_engine import RiskRewardEngine, RiskRewardEstimate


class TestRiskRewardEngine:
    def setup_method(self):
        self.engine = RiskRewardEngine()

    def test_empty_estimate(self):
        est = self.engine.estimate()
        assert est.downside_risk_pct is None
        assert est.upside_potential_pct is None
        assert est.reward_risk_ratio is None
        assert est.action_guidance == "wait"
        assert est.confidence == "unknown"

    def test_with_technical_signals(self):
        signals = {
            "ma20": 95.0,
            "ma50": 90.0,
            "ma200": 80.0,
            "atr14": 3.0,
            "atr14_pct": 3.0,
            "support_levels": [85.0, 82.0],
            "resistance_levels": [110.0, 115.0],
        }
        est = self.engine.estimate(
            technical_signals=signals,
            last_close=100.0,
        )
        assert est.downside_risk_pct is not None
        assert est.downside_risk_pct > 0
        assert est.upside_potential_pct is not None
        assert est.reward_risk_ratio is not None

    def test_thesis_broken_avoid(self):
        class FakeFundamental:
            fundamental_status = "red"
            thesis_broken = True
            target_price = None
            forward_pe = None
            pe_ttm = None
            revenue_growth_summary = ""

        est = self.engine.estimate(
            fundamental=FakeFundamental(),
            last_close=100.0,
        )
        assert est.action_guidance == "avoid"

    def test_action_guidance_reduce_now(self):
        class FakeFundamental:
            fundamental_status = "red"
            thesis_broken = True
            target_price = None
            forward_pe = None
            pe_ttm = None
            revenue_growth_summary = ""

        class FakeSnapshot:
            is_holding = True
            position_pct = 0.10

        est = self.engine.estimate(
            fundamental=FakeFundamental(),
            snapshot=FakeSnapshot(),
            last_close=100.0,
        )
        assert est.action_guidance == "reduce_now"

    def test_position_size(self):
        from app.services.investment_thesis import get_thesis
        thesis = get_thesis("AMD")
        est = self.engine.estimate(
            investment_thesis=thesis,
            last_close=100.0,
        )
        assert est.max_position_pct > 0
        assert est.position_size_label != "none"

    def test_to_dict(self):
        est = self.engine.estimate(last_close=100.0)
        d = est.to_dict()
        assert isinstance(d, dict)
        assert "action_guidance" in d
        assert "confidence" in d
