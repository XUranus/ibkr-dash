"""Daily Review evidence card dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.utils.dates import now_iso


@dataclass
class SymbolEvidenceCard:
    """Evidence card for a single symbol in the daily review."""

    symbol: str
    normalized_symbol: str
    report_date: str
    # Price action
    day_change_percent: float | None = None
    week_change_percent: float | None = None
    # Account impact
    daily_pnl: float | None = None
    contribution_ratio: float | None = None
    weight: float | None = None
    # Public context
    news_summary: str | None = None
    valuation_note: str | None = None
    sector_context: str | None = None
    technical_levels: dict[str, Any] = field(default_factory=dict)
    # Quality
    evidence_quality: str = "medium"  # high | medium | low
    data_limitations: list[str] = field(default_factory=list)
    source_tools: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict:
        """Return a plain dict representation of the symbol evidence card."""
        return {
            "symbol": self.symbol,
            "normalized_symbol": self.normalized_symbol,
            "report_date": self.report_date,
            "day_change_percent": self.day_change_percent,
            "week_change_percent": self.week_change_percent,
            "daily_pnl": self.daily_pnl,
            "contribution_ratio": self.contribution_ratio,
            "weight": self.weight,
            "news_summary": self.news_summary,
            "valuation_note": self.valuation_note,
            "sector_context": self.sector_context,
            "technical_levels": self.technical_levels,
            "evidence_quality": self.evidence_quality,
            "data_limitations": self.data_limitations,
            "source_tools": self.source_tools,
            "created_at": self.created_at or now_iso(),
        }


@dataclass
class MacroEvidenceCard:
    """Evidence card for macro/sector context."""

    report_date: str
    market_regime: str | None = None  # risk_on, risk_off, mixed, uncertain
    risk_sentiment: str | None = None  # positive, negative, neutral
    key_macro_events: list[str] = field(default_factory=list)
    sector_highlights: list[str] = field(default_factory=list)
    benchmark_summary: dict[str, Any] = field(default_factory=dict)
    evidence_quality: str = "medium"
    data_limitations: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict:
        """Return a plain dict representation of the macro evidence card."""
        return {
            "report_date": self.report_date,
            "market_regime": self.market_regime,
            "risk_sentiment": self.risk_sentiment,
            "key_macro_events": self.key_macro_events,
            "sector_highlights": self.sector_highlights,
            "benchmark_summary": self.benchmark_summary,
            "evidence_quality": self.evidence_quality,
            "data_limitations": self.data_limitations,
            "created_at": self.created_at or now_iso(),
        }


def build_fallback_symbol_card(
    *, symbol: str, normalized_symbol: str, report_date: str,
    position_item: dict, reason: str,
) -> SymbolEvidenceCard:
    """Build a low-quality fallback symbol card when full evidence is unavailable."""
    return SymbolEvidenceCard(
        symbol=symbol,
        normalized_symbol=normalized_symbol,
        report_date=report_date,
        daily_pnl=position_item.get("daily_pnl"),
        contribution_ratio=position_item.get("contribution_ratio"),
        weight=position_item.get("weight"),
        day_change_percent=position_item.get("daily_change_percent"),
        evidence_quality="low",
        data_limitations=[f"Fallback card: {reason[:200]}"],
        created_at=now_iso(),
    )


def build_fallback_macro_card(*, report_date: str, benchmark_context: dict, reason: str) -> MacroEvidenceCard:
    """Build a low-quality fallback macro card when full evidence is unavailable."""
    return MacroEvidenceCard(
        report_date=report_date,
        market_regime="uncertain",
        risk_sentiment="neutral",
        benchmark_summary=benchmark_context,
        evidence_quality="low",
        data_limitations=[f"Fallback macro card: {reason[:200]}"],
        created_at=now_iso(),
    )
