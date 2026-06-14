"""Pydantic output models for all agent structured outputs.

These models define the schema that LLM outputs must conform to.
Uses FlexibleModel with extra="allow" for resilience against unexpected fields.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FlexibleModel(BaseModel):
    """Base model that allows extra fields for forward compatibility."""

    model_config = ConfigDict(extra="allow")


class ScoreItem(FlexibleModel):
    """A single scored dimension within a trade decision or review."""

    score: float | None = 0
    max_score: float = 0
    reason: str = ""
    applicable: bool = True


class TradeDecisionOutput(FlexibleModel):
    """Structured output for trade decision analysis."""

    symbol: str | None = None
    decision_type: str = ""
    overall_score: float = 0
    rating: str | None = None
    action: str = "watchlist"
    confidence: str = "low"
    decision_summary: str = ""
    score_detail: dict[str, ScoreItem] = Field(default_factory=dict)
    position_advice: dict[str, Any] = Field(default_factory=dict)
    execution_plan: dict[str, Any] = Field(default_factory=dict)
    key_reasons: list[str] = Field(default_factory=list)
    major_risks: list[str] = Field(default_factory=list)
    review_warnings: list[str] = Field(default_factory=list)
    data_limitations: list[str] = Field(default_factory=list)
    evidence_used: list[str] = Field(default_factory=list)

    @field_validator("key_reasons", "major_risks", "review_warnings", "data_limitations", "evidence_used", mode="before")
    @classmethod
    def _list_of_strings(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            return [str(value)]
        return [str(item) for item in value]

    @field_validator("action", "confidence", "rating", "decision_summary", "symbol", "decision_type", mode="before")
    @classmethod
    def _normalize_string_fields(cls, value: Any, info: Any) -> Any:
        field_name = info.field_name if hasattr(info, "field_name") else ""

        if value is None:
            defaults = {
                "action": "watchlist",
                "confidence": "low",
                "rating": "neutral",
                "decision_summary": "LLM output missing summary; using conservative default.",
            }
            return defaults.get(field_name)

        if isinstance(value, list):
            if len(value) == 0:
                defaults = {
                    "action": "watchlist",
                    "confidence": "low",
                    "rating": "neutral",
                    "decision_summary": "LLM output missing summary; using conservative default.",
                }
                return defaults.get(field_name)
            first = value[0]
            if field_name == "action":
                allowed = {"add", "add_small", "add_batch", "hold", "reduce", "reduce_batch", "sell", "wait", "avoid", "watchlist"}
                for item in value:
                    if str(item) in allowed:
                        return str(item)
                return str(first)
            if field_name == "confidence":
                allowed = {"high", "medium", "low"}
                for item in value:
                    if str(item) in allowed:
                        return str(item)
                return str(first)
            if field_name == "rating":
                allowed = {"strong_buy_or_hold", "positive", "neutral", "negative"}
                for item in value:
                    if str(item) in allowed:
                        return str(item)
                return str(first)
            if field_name == "decision_summary":
                return "; ".join(str(v) for v in value)
            return str(first)

        if isinstance(value, dict):
            for key in ("value", "text", "summary", "action", "confidence", "rating"):
                if key in value and value[key] is not None:
                    return str(value[key])
            return json.dumps(value, ensure_ascii=False)

        return str(value)


class TradeReviewOutput(FlexibleModel):
    """Structured output for trade review analysis."""

    symbol: str | None = None
    review_type: str | None = None
    overall_score: float = 0
    rating: str | None = None
    score_detail: dict[str, ScoreItem] = Field(default_factory=dict)
    summary: str | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    mistake_tags: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)
    data_limitations: list[str] = Field(default_factory=list)
    evidence_used: list[str] = Field(default_factory=list)

    @field_validator("strengths", "weaknesses", "mistake_tags", "improvement_suggestions", "data_limitations", "evidence_used", mode="before")
    @classmethod
    def _list_of_strings(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            return [str(value)]
        return [str(item) for item in value]


class DailyPositionReviewOutput(FlexibleModel):
    """Structured output for daily position review."""

    report_date: str
    summary: str | None = None
    account_conclusion: str | None = None
    attribution_summary: str | None = None
    major_contributors_analysis: list[dict[str, Any]] = Field(default_factory=list)
    major_drags_analysis: list[dict[str, Any]] = Field(default_factory=list)
    focus_symbol_analyses: list[dict[str, Any]] = Field(default_factory=list)
    market_context: str | None = None
    risk_analysis: str | None = None
    tomorrow_watchlist: list[dict[str, Any]] = Field(default_factory=list)
    operation_observation: str | None = None
    data_limitations: list[str] = Field(default_factory=list)
    evidence_used: list[str] = Field(default_factory=list)

    @field_validator("major_contributors_analysis", "major_drags_analysis", "focus_symbol_analyses", "tomorrow_watchlist", mode="before")
    @classmethod
    def _list_of_dicts(cls, value: Any) -> list[dict[str, Any]]:
        return value if isinstance(value, list) else []

    @field_validator("data_limitations", "evidence_used", mode="before")
    @classmethod
    def _list_of_strings(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            return [str(value)]
        return [str(item) for item in value]


class RiskAssessmentOutput(FlexibleModel):
    """Structured output for risk assessment."""

    overall_risk_score: float = 0
    risk_level: str = "medium"
    summary: str = ""
    concentration_risk: dict[str, Any] = Field(default_factory=dict)
    sector_exposure: dict[str, Any] = Field(default_factory=dict)
    liquidity_risk: dict[str, Any] = Field(default_factory=dict)
    stress_test: dict[str, Any] = Field(default_factory=dict)
    key_risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    watch_points: list[str] = Field(default_factory=list)
    data_limitations: list[str] = Field(default_factory=list)
    evidence_used: list[str] = Field(default_factory=list)

    @field_validator("key_risks", "recommendations", "watch_points", "data_limitations", "evidence_used", mode="before")
    @classmethod
    def _list_of_strings(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            return [str(value)]
        return [str(item) for item in value]
