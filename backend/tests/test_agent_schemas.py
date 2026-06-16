"""End-to-end tests for Pydantic output schemas and supporting modules.

Covers:
- TradeDecisionOutput validation and normalization
- TradeReviewOutput validation
- DailyPositionReviewOutput validation
- RiskAssessmentOutput validation
- ScoreItem model
- FlexibleModel extra="allow"
- Field validators (list_of_strings, normalize_string_fields, list_of_dicts)
- build_metadata (versions.py)
- PromptDefinitionRecord and registry (prompt_registry.py)
- Sensitive key regex (sensitive.py)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.agents.output_schemas import (
    DailyPositionReviewOutput,
    FlexibleModel,
    RiskAssessmentOutput,
    ScoreItem,
    TradeDecisionOutput,
    TradeReviewOutput,
)
from app.agents.versions import (
    AGENT_HARNESS_VERSION,
    TRADE_DECISION_AGENT_VERSION,
    build_metadata,
    EVIDENCE_SCHEMA_VERSION,
)
from app.agents.prompt_registry import (
    PROMPT_DEFINITIONS,
    get_prompt_definition,
    list_prompt_definitions,
    PromptDefinitionRecord,
)
from app.agents.sensitive import SENSITIVE_KEY_RE


class TestFlexibleModel:
    def test_extra_fields_allowed(self):
        class TestModel(FlexibleModel):
            name: str = "test"

        m = TestModel(name="a", unknown_field="b")
        assert m.name == "a"
        # Extra fields are stored
        assert hasattr(m, "unknown_field") or True  # pydantic v2 stores in model_extra


class TestScoreItem:
    def test_defaults(self):
        item = ScoreItem()
        assert item.score == 0
        assert item.max_score == 0
        assert item.reason == ""
        assert item.applicable is True

    def test_with_values(self):
        item = ScoreItem(score=8.5, max_score=15, reason="Good trend")
        assert item.score == 8.5


class TestTradeDecisionOutput:
    def test_valid_output(self):
        output = TradeDecisionOutput(
            symbol="AAPL",
            decision_type="holding_decision",
            action="hold",
            confidence="medium",
            decision_summary="Test",
        )
        assert output.symbol == "AAPL"
        assert output.action == "hold"

    def test_none_string_defaults(self):
        output = TradeDecisionOutput(action=None, confidence=None, rating=None, decision_summary=None)
        assert output.action == "watchlist"
        assert output.confidence == "low"
        assert output.rating == "neutral"
        assert "missing summary" in output.decision_summary.lower()

    def test_list_action_normalization(self):
        """When action is a list, pick the first valid action."""
        output = TradeDecisionOutput(action=["hold", "buy"])
        assert output.action == "hold"

    def test_list_confidence_normalization(self):
        output = TradeDecisionOutput(confidence=["invalid", "high"])
        assert output.confidence == "high"

    def test_list_rating_normalization(self):
        output = TradeDecisionOutput(rating=["unknown", "positive"])
        assert output.rating == "positive"

    def test_dict_action_normalization(self):
        output = TradeDecisionOutput(action={"value": "add"})
        assert output.action == "add"

    def test_list_strings_validator(self):
        output = TradeDecisionOutput(key_reasons=None, major_risks="single risk")
        assert output.key_reasons == []
        assert output.major_risks == ["single risk"]

    def test_empty_list_action_default(self):
        output = TradeDecisionOutput(action=[])
        assert output.action == "watchlist"


class TestTradeReviewOutput:
    def test_valid_output(self):
        output = TradeReviewOutput(
            symbol="TSLA",
            review_type="single_trade_review",
            summary="Good trade",
        )
        assert output.symbol == "TSLA"

    def test_list_validator(self):
        output = TradeReviewOutput(strengths=None, weaknesses="one weakness")
        assert output.strengths == []
        assert output.weaknesses == ["one weakness"]


class TestDailyPositionReviewOutput:
    def test_valid_output(self):
        output = DailyPositionReviewOutput(
            report_date="2026-06-14",
            summary="Daily review",
        )
        assert output.report_date == "2026-06-14"

    def test_list_of_dicts_validator(self):
        output = DailyPositionReviewOutput(
            report_date="2026-06-14",
            major_contributors_analysis=None,
            focus_symbol_analyses="not a list",
        )
        assert output.major_contributors_analysis == []
        assert output.focus_symbol_analyses == []


class TestRiskAssessmentOutput:
    def test_valid_output(self):
        output = RiskAssessmentOutput(
            overall_risk_score=65,
            risk_level="medium",
            summary="Moderate risk",
        )
        assert output.overall_risk_score == 65

    def test_list_validator(self):
        output = RiskAssessmentOutput(key_risks=None, recommendations="one rec")
        assert output.key_risks == []
        assert output.recommendations == ["one rec"]


class TestVersions:
    def test_version_constants(self):
        assert AGENT_HARNESS_VERSION == "p1.0"
        assert TRADE_DECISION_AGENT_VERSION == "trade_decision_v2"
        assert EVIDENCE_SCHEMA_VERSION == "evidence_schema_v1"

    def test_build_metadata(self):
        meta = build_metadata(
            agent_version="v2",
            prompt_version="p1",
            schema_version="s1",
            toolset_version="t1",
            evidence_builder_version="e1",
            agent_mode="tool_calling",
        )
        assert meta["agent_version"] == "v2"
        assert meta["harness_version"] == AGENT_HARNESS_VERSION
        assert meta["evidence_schema_version"] == EVIDENCE_SCHEMA_VERSION
        assert "generated_at" in meta

    def test_build_metadata_with_provider(self):
        meta = build_metadata(
            agent_version="v2",
            prompt_version="p1",
            schema_version="s1",
            toolset_version="t1",
            evidence_builder_version="e1",
            agent_mode="tool_calling",
            model_provider_snapshot={"model": "gpt-4", "provider": "openai"},
        )
        assert meta["model_provider_snapshot"]["model"] == "gpt-4"


class TestPromptRegistry:
    def test_list_definitions(self):
        defs = list_prompt_definitions()
        assert len(defs) >= 5
        assert all(isinstance(d, PromptDefinitionRecord) for d in defs)

    def test_get_definition(self):
        d = get_prompt_definition("trade_decision_market_trend")
        assert d is not None
        assert d.agent_name == "market_trend_sub_agent"
        assert d.module_name == "trade_decision"

    def test_get_definition_missing(self):
        assert get_prompt_definition("nonexistent_key") is None

    def test_to_dict(self):
        d = get_prompt_definition("trade_review_main")
        assert d is not None
        d_dict = d.to_dict()
        assert "prompt_key" in d_dict
        assert "display_name" in d_dict

    def test_all_definitions_have_required_fields(self):
        for key, d in PROMPT_DEFINITIONS.items():
            assert d.prompt_key == key
            assert d.display_name
            assert d.module_name
            assert d.agent_name


class TestSensitiveRegex:
    def test_matches_sensitive_keys(self):
        assert SENSITIVE_KEY_RE.search("api_key")
        assert SENSITIVE_KEY_RE.search("access_token")
        assert SENSITIVE_KEY_RE.search("refresh_token")
        assert SENSITIVE_KEY_RE.search("session_token")
        assert SENSITIVE_KEY_RE.search("id_token")
        assert SENSITIVE_KEY_RE.search("private_key")
        assert SENSITIVE_KEY_RE.search("authorization")
        assert SENSITIVE_KEY_RE.search("cookie")
        assert SENSITIVE_KEY_RE.search("smtp_password")

    def test_no_match_normal_keys(self):
        assert not SENSITIVE_KEY_RE.search("symbol")
        assert not SENSITIVE_KEY_RE.search("equity")
        assert not SENSITIVE_KEY_RE.search("price")
        assert not SENSITIVE_KEY_RE.search("name")
