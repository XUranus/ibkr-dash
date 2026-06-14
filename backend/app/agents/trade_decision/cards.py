"""Trade Decision card dataclasses.

High-density summary cards consumed by the Composer and RiskGate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.utils.dates import now_iso


class CardStance:
    """Constants representing the directional stance of an analysis card."""

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
        """Return a plain dict of all card fields."""
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
    # TechnicalSignalEngine outputs
    technical_signals: dict = field(default_factory=dict)
    trend_break_level: str = "unknown"  # none | warning | broken | severe | unknown
    trend_break_reasons: list[str] = field(default_factory=list)
    support_levels: list[float] = field(default_factory=list)
    resistance_levels: list[float] = field(default_factory=list)
    relative_strength_score: float | None = None

    def to_dict(self) -> dict:
        """Return a plain dict of all card fields."""
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
    # FundamentalChangeEngine outputs
    fundamental_status: str = "unknown"  # green | yellow | orange | red | unknown
    thesis_broken: bool = False
    change_signals: list[str] = field(default_factory=list)
    positive_signals: list[str] = field(default_factory=list)
    negative_signals: list[str] = field(default_factory=list)
    revenue_growth_trend: str | None = None
    margin_trend: str | None = None
    cash_flow_trend: str | None = None
    guidance_change: str | None = None

    def to_dict(self) -> dict:
        """Return a plain dict of all card fields."""
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
        """Return a plain dict of all card fields."""
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class RiskRewardCard:
    """Risk/reward assessment card produced by deterministic engines."""

    symbol: str = ""
    decision_type: str = ""
    summary: str = ""
    score: float = 0
    max_score: float = 15
    stance: str = CardStance.INSUFFICIENT_DATA
    upside_potential_pct: float | None = None
    downside_risk_pct: float | None = None
    reward_risk_ratio: float | None = None
    max_position_pct: float | None = None
    wait_for_pullback: bool = False
    wait_for_pullback_pct: float | None = None
    pullback_entry_level: float | None = None
    action_guidance: str | None = None
    position_size_label: str = "unknown"
    key_points: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    evidence_quality: str = "low"
    data_limitations: list[str] = field(default_factory=list)
    created_at: str = ""
    # RiskRewardEngine outputs
    downside_scenarios: list[dict] = field(default_factory=list)
    upside_scenarios: list[dict] = field(default_factory=list)
    stop_add_level: float | None = None
    invalidation_level: float | None = None
    trim_level: float | None = None
    risk_reward_confidence: str = "unknown"

    def to_dict(self) -> dict:
        """Return a plain dict of all card fields."""
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class TradeDecisionCardPack:
    """Container for all sub-agent cards — consumed by Composer and RiskGate."""

    decision_type: str
    symbol: str
    account_facts: dict
    account_fit_card: AccountFitCard | None = None
    market_trend_card: MarketTrendCard | None = None
    fundamental_valuation_card: FundamentalValuationCard | None = None
    event_catalyst_card: EventCatalystCard | None = None
    risk_reward_card: RiskRewardCard | None = None
    investment_thesis: dict | None = None

    def to_dict(self) -> dict:
        return {
            "decision_type": self.decision_type,
            "symbol": self.symbol,
            "account_facts": self.account_facts,
            "account_fit_card": self.account_fit_card.to_dict() if self.account_fit_card else None,
            "market_trend_card": self.market_trend_card.to_dict() if self.market_trend_card else None,
            "fundamental_valuation_card": self.fundamental_valuation_card.to_dict() if self.fundamental_valuation_card else None,
            "event_catalyst_card": self.event_catalyst_card.to_dict() if self.event_catalyst_card else None,
            "risk_reward_card": self.risk_reward_card.to_dict() if self.risk_reward_card else None,
            "investment_thesis": self.investment_thesis,
        }


# --- AccountFactSnapshot helper for RiskGate ---

@dataclass
class AccountFactSnapshot:
    """Lightweight snapshot of account facts used by RiskGate."""

    is_holding: bool = False
    position_pct: float | None = None
    current_position_pct: float | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


# --- Fallback card builders ---


def build_fallback_risk_reward_card(symbol: str, decision_type: str, reason: str) -> RiskRewardCard:
    """Build a RiskRewardCard with conservative defaults when data is unavailable."""
    return RiskRewardCard(
        symbol=symbol, decision_type=decision_type,
        summary="Risk/reward assessment unavailable; using conservative defaults.",
        score=0, max_score=15, stance=CardStance.INSUFFICIENT_DATA,
        evidence_quality="low",
        data_limitations=[f"Risk/reward fallback: {reason[:200]}"],
        created_at=now_iso(),
    )


def build_fallback_account_fit_card(symbol: str, decision_type: str, reason: str) -> AccountFitCard:
    """Build an AccountFitCard with conservative defaults when data is unavailable.

    Args:
        symbol: Ticker symbol.
        decision_type: Type of trade decision (e.g. "buy", "sell").
        reason: Explanation of why the fallback is being used.

    Returns:
        An AccountFitCard with zeroed scores and the reason recorded as a data limitation.
    """
    return AccountFitCard(
        symbol=symbol, decision_type=decision_type,
        summary="Account fit assessment unavailable; using conservative defaults.",
        score=0, max_score=20, stance=CardStance.INSUFFICIENT_DATA,
        evidence_quality="low",
        data_limitations=[f"Account fit fallback: {reason[:200]}"],
        created_at=now_iso(),
    )


def build_fallback_market_trend_card(symbol: str, decision_type: str, reason: str) -> MarketTrendCard:
    """Build a MarketTrendCard with conservative defaults when data is unavailable.

    Args:
        symbol: Ticker symbol.
        decision_type: Type of trade decision (e.g. "buy", "sell").
        reason: Explanation of why the fallback is being used.

    Returns:
        A MarketTrendCard with zeroed scores and the reason recorded as a data limitation.
    """
    return MarketTrendCard(
        symbol=symbol, decision_type=decision_type,
        summary="Public market data insufficient; using conservative trend judgment.",
        score=0, max_score=15, stance=CardStance.INSUFFICIENT_DATA,
        evidence_quality="low",
        data_limitations=[f"Market trend fallback: {reason[:200]}"],
        created_at=now_iso(),
    )


def build_fallback_fundamental_card(symbol: str, decision_type: str, reason: str) -> FundamentalValuationCard:
    """Build a FundamentalValuationCard with conservative defaults when data is unavailable.

    Args:
        symbol: Ticker symbol.
        decision_type: Type of trade decision (e.g. "buy", "sell").
        reason: Explanation of why the fallback is being used.

    Returns:
        A FundamentalValuationCard with zeroed scores and the reason recorded as a data limitation.
    """
    return FundamentalValuationCard(
        symbol=symbol, decision_type=decision_type,
        summary="Fundamental and valuation data insufficient; using conservative defaults.",
        score=0, max_score=35, stance=CardStance.INSUFFICIENT_DATA,
        evidence_quality="low",
        data_limitations=[f"Fundamental fallback: {reason[:200]}"],
        created_at=now_iso(),
    )


def build_fallback_event_card(symbol: str, decision_type: str, reason: str) -> EventCatalystCard:
    """Build an EventCatalystCard with conservative defaults when data is unavailable.

    Args:
        symbol: Ticker symbol.
        decision_type: Type of trade decision (e.g. "buy", "sell").
        reason: Explanation of why the fallback is being used.

    Returns:
        An EventCatalystCard with zeroed scores and the reason recorded as a data limitation.
    """
    return EventCatalystCard(
        symbol=symbol, decision_type=decision_type,
        summary="Public news and event data insufficient; using conservative analysis.",
        score=0, max_score=5, stance=CardStance.INSUFFICIENT_DATA,
        evidence_quality="low",
        data_limitations=[f"Event catalyst fallback: {reason[:200]}"],
        created_at=now_iso(),
    )
