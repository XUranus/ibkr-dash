"""End-to-end tests for evidence pack builders and evidence summary.

Covers:
- empty_evidence_pack scaffold
- build_trade_decision_evidence_pack
- build_trade_review_evidence_pack
- build_daily_position_review_evidence_pack
- build_daily_position_review_evidence_pack_from_cards
- build_evidence_summary (frontend-safe)
- Sensitive key redaction in summaries
- _select_review_trades prioritization
- Section budget application
"""

from __future__ import annotations

from app.agents.evidence import (
    build_daily_position_review_evidence_pack,
    build_daily_position_review_evidence_pack_from_cards,
    build_evidence_summary,
    build_trade_decision_evidence_pack,
    build_trade_review_evidence_pack,
    empty_evidence_pack,
    _select_review_trades,
    _is_sensitive_key,
    _sanitize_value,
)


class TestEmptyEvidencePack:
    def test_basic_scaffold(self):
        pack = empty_evidence_pack(agent_name="test_agent", agent_task="test_task")
        assert pack["agent_name"] == "test_agent"
        assert pack["agent_task"] == "test_task"
        assert pack["symbol"] is None
        assert isinstance(pack["data_sources"], dict)
        assert isinstance(pack["facts"], list)
        assert isinstance(pack["data_quality"], dict)

    def test_with_symbol_and_date(self):
        pack = empty_evidence_pack(
            agent_name="trade", agent_task="decision", symbol="AAPL", report_date="2026-06-14",
        )
        assert pack["symbol"] == "AAPL"
        assert pack["report_date"] == "2026-06-14"

    def test_with_user_question(self):
        pack = empty_evidence_pack(
            agent_name="copilot", agent_task="answer", user_question="What's my risk?",
        )
        assert pack["user_question"] == "What's my risk?"


class TestTradeDecisionEvidencePack:
    def test_builds_from_raw(self):
        raw = {
            "symbol": "AAPL",
            "decision_type": "holding_decision",
            "account_context": {"equity": 100000},
            "position_context": [{"symbol": "AAPL", "weight": 0.15}],
            "market_context": {"price": 150},
            "data_quality": {"missing_fields": ["news"]},
        }
        pack = build_trade_decision_evidence_pack(raw)
        assert pack["agent_name"] == "trade_decision_agent"
        assert pack["symbol"] == "AAPL"
        assert pack["decision_type"] == "holding_decision"
        assert pack["account_context"]["equity"] == 100000
        assert "budget_report" in pack

    def test_builds_from_empty(self):
        pack = build_trade_decision_evidence_pack({})
        assert pack["agent_name"] == "trade_decision_agent"
        # account_context defaults to {} when not provided
        assert isinstance(pack["account_context"], dict)

    def test_builds_from_none(self):
        pack = build_trade_decision_evidence_pack(None)
        assert pack["agent_name"] == "trade_decision_agent"


class TestTradeReviewEvidencePack:
    def test_builds_from_raw(self):
        raw = {
            "symbol": "TSLA",
            "review_type": "single_trade_review",
            "trade_facts": {
                "trades": [{"side": "BUY", "amount": 5000}, {"side": "SELL", "amount": 6000}],
                "current_position": {"symbol": "TSLA", "quantity": 0},
                "is_currently_holding": False,
            },
            "performance_metrics": {"total_return_pct": 20.0},
            "data_quality": {"missing_fields": []},
        }
        pack = build_trade_review_evidence_pack(raw)
        assert pack["agent_name"] == "trade_review_agent"
        assert pack["trade_facts"]["is_currently_holding"] is False
        assert len(pack["trade_facts"]["trades"]) == 2

    def test_preserves_legacy_keys(self):
        raw = {
            "trade_facts": {"trades": []},
            "performance_metrics": {"return": 10},
            "price_context": {"price": 100},
            "benchmark_context": {"sp500": 5},
        }
        pack = build_trade_review_evidence_pack(raw)
        assert "trade_facts" in pack
        assert "performance_metrics" in pack
        assert "price_context" in pack
        assert "benchmark_context" in pack

    def test_select_review_trades_prioritization(self):
        trades = [
            {"side": "BUY", "amount": 1000, "date": "2026-01-01"},
            {"side": "BUY", "amount": 5000, "date": "2026-02-01"},
            {"side": "SELL", "amount": 3000, "date": "2026-03-01", "realized_pnl": 500},
            {"side": "SELL", "amount": 2000, "date": "2026-04-01", "realized_pnl": -200},
            {"side": "BUY", "amount": 100, "date": "2026-05-01"},
        ]
        selected = _select_review_trades(trades, limit=10)
        # First buy should be included
        assert any(t.get("date") == "2026-01-01" for t in selected)
        # All sells should be included
        sells = [t for t in selected if t.get("side") == "SELL"]
        assert len(sells) == 2

    def test_select_review_trades_non_dict(self):
        assert _select_review_trades("not a list") == []
        assert _select_review_trades([1, 2, 3]) == []


class TestDailyPositionReviewEvidencePack:
    def test_builds_from_raw(self):
        raw = {
            "report_date": "2026-06-14",
            "overview": {"total_value": 100000},
            "rankings": {"profit_contributors": [{"symbol": "AAPL"}]},
            "risk": {"risk_flags": []},
            "data_quality": {},
        }
        pack = build_daily_position_review_evidence_pack(raw)
        assert pack["agent_name"] == "daily_position_review_agent"
        assert pack["daily_position_context"]["report_date"] == "2026-06-14"

    def test_builds_from_cards(self):
        card_pack = {
            "report_date": "2026-06-14",
            "account_facts": {"overview": {"total_value": 100000}},
            "position_facts": [{"symbol": "AAPL"}],
            "rankings": {"profit_contributors": []},
            "risk": {"risk_flags": []},
            "attribution_quality": {},
            "symbol_cards": [{"normalized_symbol": "AAPL", "summary": "good"}],
            "macro_card": {"summary": "neutral"},
            "data_quality": {},
            "subagent_trace": {"symbol_agent_calls": [], "macro_agent_calls": []},
            "budget_report": {},
        }
        pack = build_daily_position_review_evidence_pack_from_cards(card_pack)
        assert pack["agent_name"] == "daily_position_review_agent"
        assert len(pack["symbol_cards"]) == 1
        assert pack["macro_card"] is not None
        assert "budget_report" in pack

    def test_cards_with_fallback_count(self):
        card_pack = {
            "report_date": "2026-06-14",
            "account_facts": {"overview": {}},
            "position_facts": [],
            "rankings": {},
            "risk": {},
            "attribution_quality": {},
            "symbol_cards": [],
            "macro_card": None,
            "data_quality": {},
            "subagent_trace": {
                "symbol_agent_calls": [{"status": "fallback"}, {"status": "ok"}],
                "macro_agent_calls": [],
            },
            "budget_report": {},
        }
        pack = build_daily_position_review_evidence_pack_from_cards(card_pack)
        assert pack["budget_report"]["subagent_fallback_count"] == 1


class TestEvidenceSummary:
    def test_build_summary_from_pack(self):
        pack = empty_evidence_pack(agent_name="test", agent_task="test")
        pack["account_context"] = {"equity": 100000}
        pack["position_context"] = [{"symbol": "AAPL"}]
        summary = build_evidence_summary(pack)
        assert "evidence_sections" in summary
        assert "data_sources" in summary
        assert "missing_data" in summary
        assert "data_limitations" in summary

    def test_summary_redacts_sensitive_keys(self):
        """Evidence summary sanitizes its own output via _sanitize_value."""
        # The summary only contains section statuses, but _sanitize_value
        # still runs on the full structure for safety.
        pack = empty_evidence_pack(agent_name="test", agent_task="test")
        pack["account_context"] = {"api_key": "secret123", "equity": 100000}
        summary = build_evidence_summary(pack)
        text = str(summary)
        # Raw secret should not leak through
        assert "secret123" not in text

    def test_sensitive_key_detection(self):
        assert _is_sensitive_key("api_key")
        assert _is_sensitive_key("access_token")
        assert _is_sensitive_key("smtp_password")
        assert _is_sensitive_key("authorization")
        assert not _is_sensitive_key("symbol")
        assert not _is_sensitive_key("equity")

    def test_sanitize_value_nested(self):
        data = {"outer": {"inner": {"api_key": "abc", "name": "test"}}}
        sanitized = _sanitize_value(data)
        assert sanitized["outer"]["inner"]["api_key"] == "[REDACTED]"
        assert sanitized["outer"]["inner"]["name"] == "test"

    def test_summary_section_statuses(self):
        pack = empty_evidence_pack(agent_name="test", agent_task="test")
        pack["account_context"] = {"equity": 100000}
        pack["market_context"] = {}
        summary = build_evidence_summary(pack)
        sections = {s["section"]: s["status"] for s in summary["evidence_sections"]}
        assert sections["account_context"] == "available"
        assert sections["market_context"] == "missing"
