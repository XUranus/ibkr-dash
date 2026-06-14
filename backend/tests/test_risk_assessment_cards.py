"""Risk assessment card tests."""

from __future__ import annotations

from app.agents.risk_assessment.cards import (
    ConcentrationRiskCard,
    RiskLevel,
    SectorThemeExposureCard,
    StressTestCard,
    classify_symbol_theme,
    build_fallback_concentration_card,
)


def test_classify_symbol_theme_nvidia():
    themes = classify_symbol_theme("NVDA")
    assert themes["semiconductor"] is True
    assert themes["ai"] is True
    assert themes["mega_cap_tech"] is True
    assert themes["china"] is False


def test_classify_symbol_theme_alibaba():
    themes = classify_symbol_theme("BABA")
    assert themes["china"] is True
    assert themes["semiconductor"] is False


def test_classify_symbol_theme_unknown():
    themes = classify_symbol_theme("XYZUNKNOWN")
    assert all(v is False for v in themes.values())


def test_concentration_card_to_dict():
    card = ConcentrationRiskCard(
        summary="Test",
        score=10,
        risk_level=RiskLevel.MEDIUM,
    )
    d = card.to_dict()
    assert d["summary"] == "Test"
    assert d["score"] == 10


def test_fallback_concentration_card():
    card = build_fallback_concentration_card("test error")
    assert card.risk_level == RiskLevel.MEDIUM
    assert len(card.data_limitations) > 0


def test_stress_test_card_to_dict():
    card = StressTestCard(
        summary="Stress test",
        scenarios=[{"name": "Market -10%", "estimated_loss": 10000}],
    )
    d = card.to_dict()
    assert len(d["scenarios"]) == 1
