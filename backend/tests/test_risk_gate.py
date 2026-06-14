"""Tests for RiskGate."""

from app.agents.trade_decision.cards import (
    AccountFitCard,
    CardStance,
    EventCatalystCard,
    FundamentalValuationCard,
    MarketTrendCard,
    RiskRewardCard,
    TradeDecisionCardPack,
)
from app.agents.trade_decision.risk_gate import (
    RiskGate,
    RiskGateResult,
    apply_risk_gate,
    make_fail_safe_result,
    ADD_LIKE_ACTIONS,
)


def _make_card_pack(
    *,
    is_holding: bool = False,
    position_pct: float = 0.0,
    trend_break_level: str = "none",
    fundamental_status: str = "unknown",
    catalyst_strength: str = "moderate",
    reward_risk_ratio: float | None = 2.0,
    account_fit_level: str = "good",
) -> TradeDecisionCardPack:
    """Build a card pack with sensible defaults for testing."""
    return TradeDecisionCardPack(
        decision_type="holding_decision",
        symbol="TEST",
        account_facts={
            "position_context": {
                "has_position": is_holding,
                "position_pct": position_pct,
            },
        },
        account_fit_card=AccountFitCard(
            symbol="TEST", decision_type="holding_decision",
            stance=CardStance.NEUTRAL, score=10, max_score=20,
            account_fit_level=account_fit_level,
            current_position_pct=position_pct,
            evidence_quality="medium",
        ),
        market_trend_card=MarketTrendCard(
            symbol="TEST", decision_type="holding_decision",
            stance=CardStance.BULLISH if trend_break_level == "none" else CardStance.BEARISH,
            score=10 if trend_break_level == "none" else 2,
            trend_break_level=trend_break_level,
            evidence_quality="medium",
        ),
        fundamental_valuation_card=FundamentalValuationCard(
            symbol="TEST", decision_type="holding_decision",
            stance=CardStance.NEUTRAL, score=20,
            fundamental_status=fundamental_status,
            evidence_quality="medium",
        ),
        event_catalyst_card=EventCatalystCard(
            symbol="TEST", decision_type="holding_decision",
            stance=CardStance.NEUTRAL, score=3,
            catalyst_strength=catalyst_strength,
            key_events=["some event"],
            evidence_quality="medium",
        ),
        risk_reward_card=RiskRewardCard(
            symbol="TEST", decision_type="holding_decision",
            stance=CardStance.BULLISH, score=10,
            reward_risk_ratio=reward_risk_ratio,
            evidence_quality="medium",
        ),
        investment_thesis={
            "symbol": "TEST",
            "role": "core_growth",
            "risk_class": "medium",
            "max_position_pct": 0.20,
            "sell_triggers": [],
            "no_add_triggers": [],
        },
    )


class TestRiskGate:
    def setup_method(self):
        self.gate = RiskGate()

    def test_no_downgrade_for_hold(self):
        pack = _make_card_pack()
        decision = {"action": "hold"}
        result = self.gate.evaluate(decision, pack)
        assert result.final_action == "hold"
        assert not result.downgraded

    def test_add_without_position_limit_blocked(self):
        pack = _make_card_pack()
        decision = {"action": "add", "position_advice": {}}
        result = self.gate.evaluate(decision, pack)
        assert result.final_action in ("hold_no_add", "wait")
        assert "missing_position_limit" in result.risk_flags

    def test_add_with_position_limit_ok(self):
        pack = _make_card_pack(reward_risk_ratio=2.5)
        decision = {
            "action": "add",
            "position_advice": {"max_position_pct": 0.20, "current_position_pct": 0.05},
            "execution_plan": {"invalid_conditions": ["跌破支撑"]},
        }
        result = self.gate.evaluate(decision, pack)
        # Should not downgrade (good R/R, has limit, has invalidation, trend none)
        assert result.final_action == "add"

    def test_trend_severe_blocks_add(self):
        pack = _make_card_pack(trend_break_level="severe")
        decision = {
            "action": "add",
            "position_advice": {"max_position_pct": 0.20, "current_position_pct": 0.05},
            "execution_plan": {"invalid_conditions": ["x"]},
        }
        result = self.gate.evaluate(decision, pack)
        assert result.final_action in ("hold_no_add", "wait")
        assert "trend_break_severe_blocked" in result.risk_flags

    def test_trend_broken_blocks_add(self):
        pack = _make_card_pack(trend_break_level="broken")
        decision = {
            "action": "add",
            "position_advice": {"max_position_pct": 0.20, "current_position_pct": 0.05},
            "execution_plan": {"invalid_conditions": ["x"]},
        }
        result = self.gate.evaluate(decision, pack)
        assert result.final_action in ("hold_no_add", "wait")
        assert "trend_break_broken_blocked" in result.risk_flags

    def test_trend_warning_downgrades_strong_add(self):
        pack = _make_card_pack(trend_break_level="warning")
        decision = {
            "action": "add",
            "position_advice": {"max_position_pct": 0.20, "current_position_pct": 0.05},
            "execution_plan": {"invalid_conditions": ["x"]},
        }
        result = self.gate.evaluate(decision, pack)
        assert result.final_action in ("add_on_pullback", "hold_no_add")
        assert "trend_break_warning_downgrade" in result.risk_flags

    def test_fundamental_red_blocks_add(self):
        pack = _make_card_pack(fundamental_status="red")
        decision = {
            "action": "add",
            "position_advice": {"max_position_pct": 0.20, "current_position_pct": 0.05},
            "execution_plan": {"invalid_conditions": ["x"]},
        }
        result = self.gate.evaluate(decision, pack)
        assert result.final_action == "wait"
        assert "fundamental_red_blocked" in result.risk_flags

    def test_weak_catalyst_downgrades(self):
        pack = _make_card_pack(catalyst_strength="weak")
        decision = {
            "action": "add",
            "position_advice": {"max_position_pct": 0.20, "current_position_pct": 0.05},
            "execution_plan": {"invalid_conditions": ["x"]},
        }
        result = self.gate.evaluate(decision, pack)
        assert result.final_action in ("hold_no_add", "wait")
        assert "weak_catalyst_downgrade" in result.risk_flags

    def test_rr_below_one_blocks_add(self):
        pack = _make_card_pack(reward_risk_ratio=0.5)
        decision = {
            "action": "add",
            "position_advice": {"max_position_pct": 0.20, "current_position_pct": 0.05},
            "execution_plan": {"invalid_conditions": ["x"]},
        }
        result = self.gate.evaluate(decision, pack)
        assert result.final_action in ("wait", "reduce_now")
        assert "rr_below_one" in result.risk_flags

    def test_position_limit_reached(self):
        pack = _make_card_pack(is_holding=True, position_pct=0.20)
        decision = {
            "action": "add",
            "position_advice": {"max_position_pct": 0.20, "current_position_pct": 0.20},
            "execution_plan": {"invalid_conditions": ["x"]},
        }
        result = self.gate.evaluate(decision, pack)
        assert result.final_action == "hold_no_add"
        assert "position_limit_reached" in result.risk_flags

    def test_panic_detection(self):
        pack = _make_card_pack(is_holding=True, position_pct=0.10)
        decision = {
            "action": "sell",
            "decision_summary": "用户想清仓",
            "key_reasons": [],
        }
        result = self.gate.evaluate(decision, pack, user_question="我要清仓割肉")
        assert result.final_action == "panic_blocked"
        assert "panic_sell_blocked" in result.risk_flags

    def test_extreme_risk_class_blocks_strong_add(self):
        pack = _make_card_pack()
        pack.investment_thesis = {
            "symbol": "TEST", "role": "trade", "risk_class": "extreme",
            "max_position_pct": 0.10, "sell_triggers": [], "no_add_triggers": [],
        }
        decision = {
            "action": "add",
            "position_advice": {"max_position_pct": 0.10, "current_position_pct": 0.02},
            "execution_plan": {"invalid_conditions": ["x"]},
        }
        result = self.gate.evaluate(decision, pack)
        assert result.final_action in ("add_on_pullback", "hold_no_add")
        assert "thesis_extreme_risk_blocked" in result.risk_flags


class TestApplyRiskGate:
    def test_applies_gate_to_decision(self):
        pack = _make_card_pack()
        decision = {"action": "hold", "confidence": "high"}
        mutated, result = apply_risk_gate(decision, pack)
        assert mutated["action"] == "hold"
        assert "risk_gate" in mutated

    def test_downgrade_add_to_hold(self):
        pack = _make_card_pack(trend_break_level="severe")
        decision = {
            "action": "add",
            "position_advice": {"max_position_pct": 0.20, "current_position_pct": 0.05},
            "execution_plan": {"invalid_conditions": ["x"]},
        }
        mutated, result = apply_risk_gate(decision, pack)
        assert mutated["action"] != "add"
        assert mutated["risk_gate"]["downgraded"] is True


class TestMakeFailSafeResult:
    def test_fail_safe(self):
        result = make_fail_safe_result("add", "test error")
        assert result.final_action == "wait"
        assert result.failed is True
        assert "risk_gate_failed" in result.risk_flags
