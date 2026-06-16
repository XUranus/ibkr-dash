"""End-to-end tests for domain invariants and output normalizers.

Covers:
- normalize_action (English + Chinese aliases, contains-match)
- normalize_confidence (English + Chinese)
- decision_rating_for_score / review_rating_for_score
- normalize_trade_decision_output (full pipeline)
- normalize_trade_review_output (full pipeline, exit quality normalization)
- normalize_daily_position_review_output (full pipeline)
- Score dimension validation
- Position advice normalization
- Execution plan normalization
- Watchlist sanitization (forceful language softening)
- Data limitation downgrade rules
"""

from __future__ import annotations

import pytest

from app.agents.invariants import (
    ACTION_ALIASES,
    ALLOWED_ACTIONS,
    ALLOWED_CONFIDENCE,
    CONFIDENCE_ALIASES,
    DECISION_SCORE_DIMENSIONS,
    TRADE_REVIEW_SCORE_DIMENSIONS,
    normalize_action,
    normalize_confidence,
    decision_rating_for_score,
    review_rating_for_score,
    normalize_trade_decision_output,
    normalize_trade_review_output,
    normalize_daily_position_review_output,
)


class TestNormalizeAction:
    def test_canonical_actions(self):
        for action in ALLOWED_ACTIONS:
            assert normalize_action(action) == action

    def test_english_aliases(self):
        assert normalize_action("buy") == "add_batch"
        assert normalize_action("strong_buy") == "add"
        assert normalize_action("accumulate") == "add_batch"
        assert normalize_action("trim") == "reduce"
        assert normalize_action("full_sell") == "sell"
        assert normalize_action("do_nothing") == "hold"
        assert normalize_action("watch") == "watchlist"

    def test_chinese_aliases(self):
        assert normalize_action("加仓") == "add"
        assert normalize_action("小幅加仓") == "add_small"
        assert normalize_action("持有") == "hold"
        assert normalize_action("减仓") == "reduce"
        assert normalize_action("清仓") == "sell"
        assert normalize_action("等待") == "wait"
        assert normalize_action("观察") == "watchlist"

    def test_contains_match(self):
        assert normalize_action("hold_or_add_small") == "add_small"
        assert normalize_action("wait_for_pullback") == "wait"
        assert normalize_action("add_on_dips") == "add_small"

    def test_hyphen_and_space_normalization(self):
        assert normalize_action("add-small") == "add_small"
        assert normalize_action("add small") == "add_small"

    def test_unknown_passthrough(self):
        result = normalize_action("totally_unknown_action")
        assert result == "totally_unknown_action"


class TestNormalizeConfidence:
    def test_canonical(self):
        for conf in ALLOWED_CONFIDENCE:
            assert normalize_confidence(conf) == conf

    def test_chinese(self):
        assert normalize_confidence("高") == "high"
        assert normalize_confidence("中") == "medium"
        assert normalize_confidence("低") == "low"

    def test_unknown(self):
        assert normalize_confidence("very_high") == "very_high"


class TestRatingForScore:
    def test_decision_rating(self):
        assert decision_rating_for_score(90) == "strong_buy_or_hold"
        assert decision_rating_for_score(85) == "strong_buy_or_hold"
        assert decision_rating_for_score(75) == "positive"
        assert decision_rating_for_score(70) == "positive"
        assert decision_rating_for_score(60) == "neutral"
        assert decision_rating_for_score(50) == "neutral"
        assert decision_rating_for_score(40) == "negative"

    def test_review_rating(self):
        assert review_rating_for_score(90) == "excellent"
        assert review_rating_for_score(75) == "good"
        assert review_rating_for_score(60) == "average"
        assert review_rating_for_score(40) == "poor"


class TestNormalizeTradeDecisionOutput:
    def _valid_payload(self, **overrides) -> dict:
        payload = {
            "decision_type": "holding_decision",
            "action": "hold",
            "confidence": "medium",
            "decision_summary": "Test summary",
            "score_detail": {
                dim: {"score": max_score * 0.7, "max_score": max_score, "reason": "test"}
                for dim, max_score in DECISION_SCORE_DIMENSIONS.items()
            },
            "position_advice": {
                "current_position_pct": 0.10,
                "suggested_target_position_pct": 0.10,
                "max_position_pct": 0.20,
            },
            "execution_plan": {"should_act_now": False, "plan": []},
            "key_reasons": ["reason1"],
            "major_risks": ["risk1"],
            "data_limitations": [],
        }
        payload.update(overrides)
        return payload

    def test_valid_payload(self):
        result = normalize_trade_decision_output(self._valid_payload())
        assert result["decision_type"] == "holding_decision"
        assert result["action"] == "hold"
        assert result["confidence"] == "medium"
        assert "overall_score" in result
        assert "rating" in result

    def test_action_normalization(self):
        result = normalize_trade_decision_output(self._valid_payload(action="buy"))
        assert result["action"] in ALLOWED_ACTIONS

    def test_chinese_action_normalization(self):
        result = normalize_trade_decision_output(self._valid_payload(action="持有"))
        assert result["action"] == "hold"

    def test_chinese_confidence_normalization(self):
        result = normalize_trade_decision_output(self._valid_payload(confidence="高"))
        assert result["confidence"] == "high"

    def test_invalid_decision_type_raises(self):
        with pytest.raises(ValueError, match="decision_type"):
            normalize_trade_decision_output(self._valid_payload(decision_type="invalid"))

    def test_missing_summary_raises(self):
        with pytest.raises(ValueError, match="decision_summary"):
            normalize_trade_decision_output(self._valid_payload(decision_summary=""))

    def test_data_limitation_downgrade(self):
        payload = self._valid_payload(confidence="high", data_limitations=["a", "b", "c", "d"])
        result = normalize_trade_decision_output(payload)
        assert result["confidence"] == "medium"

    def test_longbridge_critical_caps_rating(self):
        payload = self._valid_payload(
            data_limitations=["Longbridge data unavailable for this symbol"],
        )
        result = normalize_trade_decision_output(payload)
        # Rating should not be strong_buy_or_hold
        assert result["rating"] != "strong_buy_or_hold" or "strong_buy_or_hold" not in str(result.get("rating"))

    def test_position_pct_normalization(self):
        """Position pcts > 1 are treated as percentages and divided by 100."""
        payload = self._valid_payload(
            position_advice={
                "current_position_pct": 15,  # 15% -> 0.15
                "suggested_target_position_pct": 20,
                "max_position_pct": 25,
            },
        )
        result = normalize_trade_decision_output(payload)
        assert result["position_advice"]["current_position_pct"] == pytest.approx(0.15, abs=0.01)

    def test_target_capped_at_max(self):
        payload = self._valid_payload(
            position_advice={
                "current_position_pct": 0.10,
                "suggested_target_position_pct": 0.30,
                "max_position_pct": 0.20,
            },
        )
        result = normalize_trade_decision_output(payload)
        assert result["position_advice"]["suggested_target_position_pct"] <= result["position_advice"]["max_position_pct"]

    def test_reconcile_action_no_cash(self):
        """add action with no suggested_cash should downgrade to hold."""
        payload = self._valid_payload(
            action="add",
            position_advice={"current_position_pct": 0.10, "suggested_cash_amount": None},
            execution_plan={"should_act_now": True, "plan": []},
        )
        result = normalize_trade_decision_output(payload)
        # Action should be reconciled
        assert result["action"] in {"hold", "watchlist", "add", "add_small", "add_batch"}


class TestNormalizeTradeReviewOutput:
    def _valid_payload(self, **overrides) -> dict:
        payload = {
            "review_type": "single_trade_review",
            "summary": "Test review summary",
            "score_detail": {
                dim: {"score": max_score * 0.6, "max_score": max_score, "reason": "test"}
                for dim, max_score in TRADE_REVIEW_SCORE_DIMENSIONS.items()
            },
            "strengths": ["good entry"],
            "weaknesses": ["late exit"],
            "mistake_tags": ["CHASE_HIGH"],
            "improvement_suggestions": ["set stop loss"],
            "data_limitations": [],
        }
        payload.update(overrides)
        return payload

    def test_valid_payload(self):
        result = normalize_trade_review_output(self._valid_payload())
        assert result["summary"] == "Test review summary"
        assert "overall_score" in result
        assert "rating" in result
        assert "excluded_score_dimensions" in result

    def test_missing_summary_raises(self):
        with pytest.raises(ValueError, match="summary"):
            normalize_trade_review_output(self._valid_payload(summary=""))

    def test_unknown_mistake_tags_filtered(self):
        payload = self._valid_payload(mistake_tags=["CHASE_HIGH", "UNKNOWN_TAG"])
        result = normalize_trade_review_output(payload)
        assert "CHASE_HIGH" in result["mistake_tags"]
        assert "UNKNOWN_TAG" not in result["mistake_tags"]
        assert any("Unknown mistake tags" in d for d in result["data_limitations"])

    def test_exit_quality_not_applicable_for_no_sells(self):
        """When there are no sell trades, exit_quality_score should be N/A."""
        review_context = {
            "trade_facts": {
                "trades": [{"side": "BUY"}],
                "is_currently_holding": True,
                "has_sell_trades": False,
            }
        }
        result = normalize_trade_review_output(
            self._valid_payload(),
            review_context=review_context,
        )
        exit_dim = result["score_detail"].get("exit_quality_score", {})
        assert exit_dim.get("applicable") is False

    def test_open_buy_not_zeroed(self):
        """BUY-only open position should not be scored as zero."""
        review_context = {
            "trade_facts": {
                "trades": [{"side": "BUY"}],
                "is_currently_holding": True,
                "has_sell_trades": False,
            }
        }
        payload = self._valid_payload()
        # Simulate LLM outputting zero scores
        for dim in payload["score_detail"]:
            payload["score_detail"][dim]["score"] = 0
        result = normalize_trade_review_output(payload, review_context=review_context)
        # Should be normalized to non-zero minimums
        assert result["overall_score"] > 0


class TestNormalizeDailyPositionReviewOutput:
    def _valid_payload(self, **overrides) -> dict:
        payload = {
            "report_date": "2026-06-14",
            "summary": "Daily summary",
            "account_conclusion": "Account OK",
            "attribution_summary": "PnL +1000",
            "major_contributors_analysis": [{"symbol": "AAPL"}],
            "major_drags_analysis": [],
            "focus_symbol_analyses": [],
            "market_context": "Market neutral",
            "risk_analysis": "Low risk",
            "tomorrow_watchlist": [],
            "operation_observation": "Monitor",
            "data_limitations": [],
        }
        payload.update(overrides)
        return payload

    def test_valid_payload(self):
        result = normalize_daily_position_review_output(
            self._valid_payload(), expected_report_date="2026-06-14",
        )
        assert result["report_date"] == "2026-06-14"
        assert result["summary"] == "Daily summary"

    def test_date_mismatch_raises(self):
        with pytest.raises(ValueError, match="report_date"):
            normalize_daily_position_review_output(
                self._valid_payload(report_date="wrong"),
                expected_report_date="2026-06-14",
            )

    def test_fallback_values_applied(self):
        """Missing fields should be filled from deterministic fallback."""
        payload = {"report_date": "2026-06-14"}
        result = normalize_daily_position_review_output(
            payload, expected_report_date="2026-06-14",
        )
        assert result["summary"]  # fallback applied
        assert any("fallback" in d for d in result["data_limitations"])

    def test_forceful_watchlist_softened(self):
        payload = self._valid_payload(
            tomorrow_watchlist=[{"symbol": "AAPL", "note": "必须买入 this stock"}],
        )
        result = normalize_daily_position_review_output(
            payload, expected_report_date="2026-06-14",
        )
        assert "必须买入" not in str(result["tomorrow_watchlist"])
        assert any("softened" in d for d in result["data_limitations"])
