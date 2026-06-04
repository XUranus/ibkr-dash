"""Risk Assessment card dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.utils.dates import now_iso


class RiskLevel:
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
        return {k: v for k, v in self.__dict__.items()}


# Theme classification rules
THEME_SEMICONDUCTOR = {
    "AMD", "NVDA", "INTC", "TSM", "ASML", "AVGO", "MU", "SMCI", "QCOM", "MRVL",
    "AMAT", "LRCX", "KLAC", "ON", "TXN", "MCHP", "ARM",
}
THEME_AI = {
    "NVDA", "MSFT", "GOOGL", "AMZN", "META", "ORCL", "CRM", "PLTR", "SNOW",
    "AI", "SYM", "PATH", "MDB", "NET", "DDOG", "PANW", "CRWD", "ZS",
}
THEME_CHINA = {
    "BABA", "JD", "PDD", "BIDU", "TCEHY", "NIO", "LI", "XPEV",
    "BILI", "IQ", "MNSO", "FUTU", "TIGR", "EDU", "TAL", "YMM", "ZTO",
}
MEGA_CAP_TECH = {"AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"}
CASH_EQUIVALENT_SYMBOLS = {"SGOV", "STRC", "BIL", "SHV", "USFR", "TFLO", "BOXX"}


def classify_symbol_theme(symbol: str) -> dict[str, bool]:
    """Classify a symbol into themes using rules. No MCP needed."""
    base = str(symbol or "").upper().split(".", 1)[0]
    return {
        "semiconductor": base in THEME_SEMICONDUCTOR,
        "ai": base in THEME_AI,
        "china": base in THEME_CHINA,
        "mega_cap_tech": base in MEGA_CAP_TECH,
        "cash_equivalent": base in CASH_EQUIVALENT_SYMBOLS,
    }


def build_fallback_concentration_card(reason: str) -> ConcentrationRiskCard:
    return ConcentrationRiskCard(
        summary=f"Concentration risk assessment unavailable: {reason[:100]}",
        score=12, risk_level=RiskLevel.MEDIUM, evidence_quality="low",
        data_limitations=[f"Fallback: {reason[:200]}"],
        created_at=now_iso(),
    )


def build_fallback_sector_theme_card(reason: str) -> SectorThemeExposureCard:
    return SectorThemeExposureCard(
        summary=f"Sector/theme exposure assessment unavailable: {reason[:100]}",
        score=10, risk_level=RiskLevel.MEDIUM, evidence_quality="low",
        data_limitations=[f"Fallback: {reason[:200]}"],
        created_at=now_iso(),
    )


def build_fallback_stress_test_card(reason: str) -> StressTestCard:
    return StressTestCard(
        summary=f"Stress test assessment unavailable: {reason[:100]}",
        score=10, risk_level=RiskLevel.MEDIUM, evidence_quality="low",
        data_limitations=[f"Fallback: {reason[:200]}"],
        created_at=now_iso(),
    )
