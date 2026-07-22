"""Risk Assessment card dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.utils.dates import now_iso


class RiskLevel:
    """Enumeration of risk severity levels used across risk assessment cards."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class ConcentrationRiskCard:
    """Position concentration risk assessment."""

    summary: str = ""
    score: float = 0
    max_score: float = 25
    risk_level: str = RiskLevel.LOW
    largest_position_pct: float = 0.0
    top_3_position_pct: float = 0.0
    top_5_position_pct: float = 0.0
    concentration_findings: list[str] = field(default_factory=list)
    key_risks: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    evidence_quality: str = "high"
    data_limitations: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict:
        """Return a plain dict of all card fields."""
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class SectorThemeExposureCard:
    """Sector and theme exposure risk assessment."""

    summary: str = ""
    score: float = 0
    max_score: float = 20
    risk_level: str = RiskLevel.LOW
    sector_exposures: dict = field(default_factory=dict)
    theme_exposures: dict = field(default_factory=dict)
    ai_exposure_pct: float = 0.0
    semiconductor_exposure_pct: float = 0.0
    china_exposure_pct: float = 0.0
    mega_cap_tech_exposure_pct: float = 0.0
    key_risks: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    evidence_quality: str = "low"
    data_limitations: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict:
        """Return a plain dict of all card fields."""
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class StressTestCard:
    """Stress test scenario assessment."""

    summary: str = ""
    score: float = 0
    max_score: float = 20
    risk_level: str = RiskLevel.LOW
    scenarios: list[dict] = field(default_factory=list)
    worst_case_drawdown_pct: float = 0.0
    worst_case_loss_amount: float = 0.0
    liquidity_after_stress: float = 0.0
    margin_risk_after_stress: str = "none"
    key_risks: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    evidence_quality: str = "high"
    data_limitations: list[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict:
        """Return a plain dict of all card fields."""
        return {k: v for k, v in self.__dict__.items()}


from app.core.symbol_constants import (
    CASH_EQUIVALENT_SYMBOLS,
    MEGA_CAP_TECH,
    THEME_AI,
    THEME_CHINA,
    THEME_SEMICONDUCTOR,
    classify_symbol_theme,
)


def build_fallback_concentration_card(reason: str) -> ConcentrationRiskCard:
    """Build a fallback concentration card when the real assessment fails.

    Args:
        reason: Short explanation of why the assessment could not be completed.

    Returns:
        A ConcentrationRiskCard with placeholder values and low evidence quality.
    """
    return ConcentrationRiskCard(
        summary=f"Concentration risk assessment unavailable: {reason[:100]}",
        score=12, risk_level=RiskLevel.MEDIUM, evidence_quality="low",
        data_limitations=[f"Fallback: {reason[:200]}"],
        created_at=now_iso(),
    )


def build_fallback_sector_theme_card(reason: str) -> SectorThemeExposureCard:
    """Build a fallback sector/theme exposure card when the real assessment fails.

    Args:
        reason: Short explanation of why the assessment could not be completed.

    Returns:
        A SectorThemeExposureCard with placeholder values and low evidence quality.
    """
    return SectorThemeExposureCard(
        summary=f"Sector/theme exposure assessment unavailable: {reason[:100]}",
        score=10, risk_level=RiskLevel.MEDIUM, evidence_quality="low",
        data_limitations=[f"Fallback: {reason[:200]}"],
        created_at=now_iso(),
    )


def build_fallback_stress_test_card(reason: str) -> StressTestCard:
    """Build a fallback stress test card when the real assessment fails.

    Args:
        reason: Short explanation of why the assessment could not be completed.

    Returns:
        A StressTestCard with placeholder values and low evidence quality.
    """
    return StressTestCard(
        summary=f"Stress test assessment unavailable: {reason[:100]}",
        score=10, risk_level=RiskLevel.MEDIUM, evidence_quality="low",
        data_limitations=[f"Fallback: {reason[:200]}"],
        created_at=now_iso(),
    )
