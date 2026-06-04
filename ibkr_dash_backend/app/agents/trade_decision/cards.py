"""Trade Decision card dataclasses (re-exported from shared module)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.utils.dates import now_iso


class CardStance:
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    MIXED = "mixed"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class AccountFitCard:
    """Account suitability assessment card."""

    symbol: str = ""
    decision_type: str = ""
    summary: str = ""
    score: float = 0
    max_score: float = 20
    stance: str = CardStance.INSUFFICIENT_DATA
    account_fit_level: str = "unknown"
    deployable_liquidity: float | None = None
    current_position_pct: float | None = None
    max_suggested_position_pct: float | None = None
    suggested_cash_amount: float | None = None
    position_size_label: str = "unknown"
    key_points: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    review_warnings: list[str] = field(default_factory=list)
    historical_mistake_flags: list[str] = field(default_factory=list)
    evidence_quality: str = "low"
    data_limitations: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class MarketTrendCard:
    """Market trend analysis card."""

    symbol: str = ""
    decision_type: str = ""
    summary: str = ""
    score: float = 0
    max_score: float = 15
    stance: str = CardStance.INSUFFICIENT_DATA
    price_trend: str = "unknown"
    relative_to_benchmark: str | None = None
    recent_return_pct: float | None = None
    volatility_summary: str = ""
    volume_signal: str | None = None
    support_resistance: dict = field(default_factory=dict)
    sector_view: str | None = None
    key_points: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    evidence_quality: str = "low"
    data_limitations: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class FundamentalValuationCard:
    """Fundamental and valuation analysis card."""

    symbol: str = ""
    decision_type: str = ""
    summary: str = ""
    score: float = 0
    max_score: float = 35
    stance: str = CardStance.INSUFFICIENT_DATA
    company_name: str = ""
    market_cap: float | None = None
    pe_ttm: float | None = None
    forward_pe: float | None = None
    revenue_growth_summary: str = ""
    profitability_summary: str = ""
    valuation_summary: str = ""
    peer_relative_note: str = ""
    key_points: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    evidence_quality: str = "low"
    data_limitations: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class EventCatalystCard:
    """Event catalyst analysis card."""

    symbol: str = ""
    decision_type: str = ""
    summary: str = ""
    score: float = 0
    max_score: float = 5
    stance: str = CardStance.INSUFFICIENT_DATA
    next_earnings_date: str | None = None
    recent_news_count: int = 0
    key_events: list[str] = field(default_factory=list)
    sentiment: str = "neutral"
    catalyst_strength: str = "neutral"
    risk_events: list[str] = field(default_factory=list)
    key_points: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    evidence_quality: str = "low"
    data_limitations: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def build_fallback_account_fit_card(symbol: str, decision_type: str, reason: str) -> AccountFitCard:
    return AccountFitCard(
        symbol=symbol, decision_type=decision_type,
        summary="Account fit assessment unavailable; using conservative defaults.",
        score=0, max_score=20, stance=CardStance.INSUFFICIENT_DATA,
        evidence_quality="low",
        data_limitations=[f"Account fit fallback: {reason[:200]}"],
        created_at=now_iso(),
    )


def build_fallback_market_trend_card(symbol: str, decision_type: str, reason: str) -> MarketTrendCard:
    return MarketTrendCard(
        symbol=symbol, decision_type=decision_type,
        summary="Public market data insufficient; using conservative trend judgment.",
        score=0, max_score=15, stance=CardStance.INSUFFICIENT_DATA,
        evidence_quality="low",
        data_limitations=[f"Market trend fallback: {reason[:200]}"],
        created_at=now_iso(),
    )


def build_fallback_fundamental_card(symbol: str, decision_type: str, reason: str) -> FundamentalValuationCard:
    return FundamentalValuationCard(
        symbol=symbol, decision_type=decision_type,
        summary="Fundamental and valuation data insufficient; using conservative defaults.",
        score=0, max_score=35, stance=CardStance.INSUFFICIENT_DATA,
        evidence_quality="low",
        data_limitations=[f"Fundamental fallback: {reason[:200]}"],
        created_at=now_iso(),
    )


def build_fallback_event_card(symbol: str, decision_type: str, reason: str) -> EventCatalystCard:
    return EventCatalystCard(
        symbol=symbol, decision_type=decision_type,
        summary="Public news and event data insufficient; using conservative analysis.",
        score=0, max_score=5, stance=CardStance.INSUFFICIENT_DATA,
        evidence_quality="low",
        data_limitations=[f"Event catalyst fallback: {reason[:200]}"],
        created_at=now_iso(),
    )
