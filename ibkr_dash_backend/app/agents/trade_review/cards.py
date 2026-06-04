"""Trade Review card dataclasses.

These represent structured intermediate results used during trade review analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.utils.dates import now_iso


@dataclass
class TradeLifecycleCard:
    """Facts about a trade's lifecycle: entry, holds, exits."""

    symbol: str = ""
    review_type: str = ""  # single_trade_review | symbol_level_review
    trade_id: str | None = None
    first_buy_date: str | None = None
    last_trade_date: str | None = None
    total_buys: int = 0
    total_sells: int = 0
    is_currently_holding: bool = False
    lifecycle_stage: str = "unknown"  # open | closed | partial
    total_quantity_bought: float = 0.0
    total_quantity_sold: float = 0.0
    average_entry_price: float = 0.0
    average_exit_price: float = 0.0
    total_commission: float = 0.0
    realized_pnl: float = 0.0
    holding_days: int = 0
    data_limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class BehaviorPatternCard:
    """Analysis of trading behavior patterns."""

    summary: str = ""
    behavior_score: float = 0
    max_score: float = 30
    recurring_patterns: list[str] = field(default_factory=list)
    positive_patterns: list[str] = field(default_factory=list)
    negative_patterns: list[str] = field(default_factory=list)
    mistake_tags: list[str] = field(default_factory=list)
    improvement_notes: list[str] = field(default_factory=list)
    data_limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class OpportunityCostCard:
    """Analysis of opportunity cost vs benchmarks."""

    summary: str = ""
    opportunity_cost_score: float = 0
    max_score: float = 20
    benchmark_comparison: dict = field(default_factory=dict)
    missed_upside: float = 0.0
    avoided_downside: float = 0.0
    capital_redeployment_note: str = ""
    data_limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class TradeReviewCardPack:
    """Container for all trade review cards."""

    lifecycle_card: TradeLifecycleCard = field(default_factory=TradeLifecycleCard)
    behavior_card: BehaviorPatternCard = field(default_factory=BehaviorPatternCard)
    opportunity_card: OpportunityCostCard = field(default_factory=OpportunityCostCard)
    evidence_quality: str = "low"
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "lifecycle_card": self.lifecycle_card.to_dict(),
            "behavior_card": self.behavior_card.to_dict(),
            "opportunity_card": self.opportunity_card.to_dict(),
            "evidence_quality": self.evidence_quality,
            "created_at": self.created_at,
        }


def build_fallback_lifecycle_card(symbol: str, reason: str) -> TradeLifecycleCard:
    return TradeLifecycleCard(
        symbol=symbol,
        summary=f"Trade lifecycle data unavailable: {reason[:100]}",
        data_limitations=[f"Fallback: {reason[:200]}"],
    )


def build_fallback_behavior_card(reason: str) -> BehaviorPatternCard:
    return BehaviorPatternCard(
        summary=f"Behavior pattern analysis unavailable: {reason[:100]}",
        behavior_score=15,
        data_limitations=[f"Fallback: {reason[:200]}"],
    )


def build_fallback_opportunity_card(reason: str) -> OpportunityCostCard:
    return OpportunityCostCard(
        summary=f"Opportunity cost analysis unavailable: {reason[:100]}",
        opportunity_cost_score=10,
        data_limitations=[f"Fallback: {reason[:200]}"],
    )
