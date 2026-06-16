"""End-to-end tests for context budget enforcement.

Covers:
- trim_text primitive
- limit_list primitive
- estimate_json_chars primitive
- compact_public_item
- compact_news_items
- compact_trade_items
- compact_position_items
- compact_data_quality
- compact_daily_position_context
- compact_single_trade_review_context
- enforce_section_budget progressive strategy
- build_budget_report
- Section-specific compactors
"""

from __future__ import annotations

import json

from app.agents.context_budget import (
    build_budget_report,
    compact_data_quality,
    compact_daily_position_context,
    compact_news_items,
    compact_position_items,
    compact_public_item,
    compact_single_trade_review_context,
    compact_trade_items,
    enforce_section_budget,
    estimate_json_chars,
    limit_list,
    trim_text,
)


class TestPrimitives:
    def test_trim_text_short(self):
        assert trim_text("hello", 10) == "hello"

    def test_trim_text_exact(self):
        assert trim_text("hello", 5) == "hello"

    def test_trim_text_long(self):
        result = trim_text("hello world", 8)
        assert len(result) <= 8
        assert result.endswith("...")

    def test_trim_text_zero_limit(self):
        assert trim_text("anything", 0) == ""

    def test_trim_text_none(self):
        assert trim_text(None, 10) == ""

    def test_limit_list_normal(self):
        assert limit_list([1, 2, 3, 4, 5], 3) == [1, 2, 3]

    def test_limit_list_from_end(self):
        assert limit_list([1, 2, 3, 4, 5], 3, from_end=True) == [3, 4, 5]

    def test_limit_list_empty(self):
        assert limit_list([], 5) == []

    def test_limit_list_non_list(self):
        assert limit_list("not a list", 5) == []

    def test_limit_list_zero(self):
        assert limit_list([1, 2], 0) == []

    def test_estimate_json_chars(self):
        assert estimate_json_chars({"a": 1}) > 0
        assert estimate_json_chars({}) == 2  # "{}"


class TestCompactors:
    def test_compact_public_item(self):
        item = {"name": "AAPL", "price": 150, "content": "very long text " * 100, "nested": {"a": 1}}
        result = compact_public_item(item)
        assert "name" in result
        assert "price" in result
        assert "content" not in result  # long text key dropped

    def test_compact_public_item_limits_fields(self):
        item = {f"key_{i}": i for i in range(20)}
        result = compact_public_item(item, max_items=5)
        assert len(result) <= 5

    def test_compact_public_item_non_dict(self):
        assert compact_public_item("not a dict") == {}

    def test_compact_news_items(self):
        news = [
            {"title": "Breaking news", "summary": "Details here", "published_at": "2026-06-14", "source": "Reuters"},
            {"headline": "Other", "description": "More info", "date": "2026-06-13"},
        ]
        result = compact_news_items(news, limit=5)
        assert len(result) == 2
        assert result[0]["title"] == "Breaking news"

    def test_compact_news_items_limit(self):
        news = [{"title": f"News {i}"} for i in range(20)]
        result = compact_news_items(news, limit=3)
        assert len(result) == 3

    def test_compact_trade_items(self):
        trades = [
            {"trade_id": "T1", "symbol": "AAPL", "side": "BUY", "quantity": 10, "price": 150, "amount": 1500},
            {"trade_id": "T2", "symbol": "TSLA", "side": "SELL", "quantity": 5, "price": 200, "amount": 1000},
        ]
        result = compact_trade_items(trades, limit=10)
        assert len(result) == 2
        assert result[0]["trade_id"] == "T1"

    def test_compact_trade_items_from_end(self):
        trades = [{"trade_id": f"T{i}", "symbol": "AAPL"} for i in range(20)]
        result = compact_trade_items(trades, limit=5)
        assert len(result) == 5

    def test_compact_position_items(self):
        positions = [
            {"symbol": "AAPL", "quantity": 100, "market_value": 15000, "weight": 0.15},
            {"symbol": "TSLA", "quantity": 50, "market_value": 10000, "weight": 0.10},
        ]
        result = compact_position_items(positions, limit=10)
        assert len(result) == 2
        assert result[0]["symbol"] == "AAPL"

    def test_compact_data_quality(self):
        dq = {
            "missing_fields": ["news", "fundamentals"],
            "warnings": ["stale data"] * 20,
            "limitations": ["no intraday"],
        }
        result = compact_data_quality(dq, warning_limit=5)
        assert len(result["warnings"]) <= 5
        assert result["missing_fields"] == ["news", "fundamentals"]


class TestEnforceSectionBudget:
    def test_fits_budget(self):
        data = {"small": "data"}
        result = enforce_section_budget("account_context", data)
        assert isinstance(result, dict)
        assert "budget_report" in result

    def test_progressive_compaction(self):
        large_data = {
            "positions": [{"symbol": f"S{i}", "data": "x" * 200} for i in range(50)],
            "news": [{"title": f"N{i}", "summary": "y" * 300} for i in range(30)],
        }
        result = enforce_section_budget("market_context", large_data, budget=2000)
        assert isinstance(result, dict)
        report = result.get("budget_report", {})
        assert report.get("truncated") is True or estimate_json_chars(result) <= 2500

    def test_data_quality_section(self):
        dq = {"missing_fields": ["a"], "warnings": ["b"] * 50, "limitations": ["c"]}
        result = enforce_section_budget("data_quality", dq)
        assert "budget_report" in result

    def test_budget_report_structure(self):
        report = build_budget_report(1000, 500, {"news": 10}, ["content"])
        assert report["original_size"] == 1000
        assert report["final_size"] == 500
        assert report["dropped_items"]["news"] == 10
        assert "content" in report["truncated_fields"]
        assert report["truncated"] is True

    def test_budget_report_no_truncation(self):
        report = build_budget_report(100, 100)
        assert report["truncated"] is False


class TestCompactDailyPositionContext:
    def test_compact_rankings(self):
        data = {
            "report_date": "2026-06-14",
            "rankings": {
                "profit_contributors": [{"symbol": f"S{i}"} for i in range(10)],
                "loss_drags": [{"symbol": f"L{i}"} for i in range(10)],
                "top_weights": [{"symbol": f"W{i}"} for i in range(10)],
            },
            "positions": [{"symbol": "SHOULD_BE_DROPPED"}],
            "symbol_public_context": {},
            "data_quality": {},
        }
        result = compact_daily_position_context(data)
        assert len(result["rankings"]["profit_contributors"]) <= 5
        assert "positions" not in result  # dropped


class TestCompactSingleTradeReviewContext:
    def test_compact_basic(self):
        data = {
            "review_context": {
                "review_type": "single_trade_review",
                "symbol": "AAPL",
                "trade_facts": {
                    "reviewed_trade_id": "T1",
                    "trades": [{"side": "BUY", "amount": 5000, "symbol": "AAPL"}],
                    "related_symbol_trades": [{"side": "BUY", "amount": 5000}, {"side": "SELL", "amount": 6000}],
                    "is_currently_holding": False,
                    "current_position": {"symbol": "AAPL", "quantity": 0},
                },
                "performance_metrics": {"total_return_pct": 20},
                "data_quality": {},
            }
        }
        result = compact_single_trade_review_context(data)
        assert "review_context" in result
        facts = result["review_context"]["review_context"]["trade_facts"]
        assert facts["reviewed_trade_id"] == "T1"
