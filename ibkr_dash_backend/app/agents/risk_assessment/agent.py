"""Risk Assessment agent.

Simplified from the original LangGraph-based implementation.
Deterministic computations + LLM report composition.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.risk_assessment.cards import (
    ConcentrationRiskCard,
    RiskLevel,
    SectorThemeExposureCard,
    StressTestCard,
    build_fallback_concentration_card,
    build_fallback_sector_theme_card,
    build_fallback_stress_test_card,
    classify_symbol_theme,
)


async def assess_risk(
    db: Any,
    llm_service: Any,
    *,
    question: str | None = None,
    prompt_service: Any = None,
) -> dict:
    """Generate a portfolio risk assessment.

    1. Load portfolio data from DB
    2. Compute concentration, sector exposure, stress test (deterministic)
    3. Call LLM for report composition
    4. Save

    Args:
        db: Database session or repository.
        llm_service: LLM service for text generation.
        question: Optional user question context.
        prompt_service: Optional admin prompt override service.

    Returns:
        Saved risk assessment document dict.
    """
    from app.agents.output_schemas import RiskAssessmentOutput
    from app.agents.prompt_runtime import resolve_runtime_prompt
    from app.agents.structured_output import StructuredOutputContract, StructuredOutputRuntime

    # Step 1: Load portfolio data
    snapshot = _load_portfolio_snapshot(db, question)

    # Step 2: Deterministic risk computations
    concentration_card = _assess_concentration(snapshot)
    sector_theme_card = _assess_sector_theme(snapshot)
    stress_test_card = _assess_stress_test(snapshot)

    # Step 3: Call LLM for report composition
    system_prompt, prompt_metadata = resolve_runtime_prompt(
        prompt_service,
        "risk_assessment_composer",
        "You are the Risk Assessment agent. Based on deterministic risk cards, compose a risk assessment report. Output strict JSON. No Markdown.",
    )
    user_prompt = _build_composer_prompt(snapshot, concentration_card, sector_theme_card, stress_test_card)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    contract = StructuredOutputContract(
        name="risk_assessment",
        agent_name="risk_assessment",
        node_name="compose",
        output_model=RiskAssessmentOutput,
        schema_hint=RiskAssessmentOutput.model_json_schema(),
        max_repair_attempts=1,
        repair_enabled=True,
        fallback_enabled=True,
        fallback_builder=lambda ctx, err, raw: _build_fallback_output(concentration_card, sector_theme_card, stress_test_card),
    )
    so_runtime = StructuredOutputRuntime(llm_service)
    result = so_runtime.generate(messages, contract)

    from app.agents.output_schemas import RiskAssessmentOutput as RAOutput
    if result.ok and result.payload:
        model = RAOutput.model_validate(result.payload)
        validated = model.model_dump()
    else:
        validated = _build_fallback_output(concentration_card, sector_theme_card, stress_test_card)

    # Step 4: Save
    document = {
        **validated,
        "assessment_type": "portfolio_risk",
        "evidence_pack": {
            "concentration_card": concentration_card.to_dict(),
            "sector_theme_card": sector_theme_card.to_dict(),
            "stress_test_card": stress_test_card.to_dict(),
            "snapshot": snapshot,
        },
        "raw_llm_response": result.raw_response if result.ok else "",
        "fallback_used": not result.ok,
        "prompt_metadata": {"risk_assessment_composer": prompt_metadata},
    }
    saved = _save_assessment(db, document)
    return saved


def _load_portfolio_snapshot(db: Any, question: str | None) -> dict:
    """Load portfolio snapshot from DB. Placeholder for real implementation."""
    if hasattr(db, "build_risk_snapshot"):
        snapshot = db.build_risk_snapshot(question=question)
        if hasattr(snapshot, "to_dict"):
            return snapshot.to_dict()
        return snapshot if isinstance(snapshot, dict) else {}
    return {
        "net_liquidation": 0,
        "cash": 0,
        "deployable_liquidity": 0,
        "positions": [],
        "total_position_value": 0,
        "top_positions": [],
        "position_count": 0,
        "largest_position_pct": 0,
        "top_3_position_pct": 0,
        "top_5_position_pct": 0,
        "cash_pct": 0,
        "margin_info": {},
        "data_quality": {},
    }


def _assess_concentration(snapshot: dict) -> ConcentrationRiskCard:
    """Deterministic concentration risk assessment."""
    findings: list[str] = []
    risks: list[str] = []
    actions: list[str] = []
    score = 0.0

    largest = snapshot.get("largest_position_pct", 0)
    top3 = snapshot.get("top_3_position_pct", 0)
    pos_count = snapshot.get("position_count", 0)
    cash_pct = snapshot.get("cash_pct", 0)

    if largest > 0.40:
        score += 20
        findings.append(f"Largest position {largest:.1%}, extreme concentration")
        risks.append("Single position over-concentrated, high drawdown risk")
    elif largest > 0.25:
        score += 14
        findings.append(f"Largest position {largest:.1%}, high concentration")
        risks.append("Single position concentration too high")
    elif largest > 0.15:
        score += 7
        findings.append(f"Largest position {largest:.1%}, moderate concentration")
    else:
        findings.append(f"Largest position {largest:.1%}, well diversified")

    if top3 > 0.70:
        score += 5
        findings.append(f"Top 3 positions total {top3:.1%}, high concentration")
        risks.append("Top 3 positions too concentrated")

    if pos_count <= 2 and largest > 0.30:
        score += 5
        findings.append(f"Only {pos_count} positions, insufficient diversification")
        risks.append("Too few positions")

    if cash_pct < 0.05:
        score += 3
        findings.append(f"Cash only {cash_pct:.1%}, insufficient liquidity buffer")

    score = min(score, 25)
    risk_level = _risk_level_from_score(score, 25)

    if risk_level in (RiskLevel.HIGH, RiskLevel.EXTREME):
        actions.append("Consider reducing largest position below 20%")
        actions.append("Increase portfolio diversification")
    elif risk_level == RiskLevel.MEDIUM:
        actions.append("Monitor largest position weight changes")

    return ConcentrationRiskCard(
        summary=f"Concentration: {risk_level}. Largest {largest:.1%}, top 3 {top3:.1%}, {pos_count} positions.",
        score=round(score, 2), max_score=25, risk_level=risk_level,
        largest_position_pct=largest, top_3_position_pct=top3,
        top_5_position_pct=snapshot.get("top_5_position_pct", 0),
        concentration_findings=findings, key_risks=risks, suggested_actions=actions,
        evidence_quality="high",
    )


def _assess_sector_theme(snapshot: dict) -> SectorThemeExposureCard:
    """Deterministic sector/theme exposure assessment using rules."""
    positions = snapshot.get("positions", [])
    total_value = snapshot.get("total_position_value", 1.0) or 1.0

    theme_map: dict[str, dict[str, float]] = {
        "semiconductor": {}, "ai": {}, "china": {}, "mega_cap_tech": {},
    }

    for pos in positions:
        symbol = pos.get("symbol", "") if isinstance(pos, dict) else ""
        pct = pos.get("position_pct", 0) if isinstance(pos, dict) else 0
        themes = classify_symbol_theme(symbol)
        for theme, is_member in themes.items():
            if is_member and theme in theme_map:
                theme_map[theme][symbol] = pct

    ai_pct = sum(theme_map["ai"].values())
    semi_pct = sum(theme_map["semiconductor"].values())
    china_pct = sum(theme_map["china"].values())
    mega_pct = sum(theme_map["mega_cap_tech"].values())

    score = 0.0
    risks: list[str] = []
    if ai_pct > 0.40:
        score += 8
        risks.append(f"AI exposure {ai_pct:.1%} is very high")
    if semi_pct > 0.30:
        score += 6
        risks.append(f"Semiconductor exposure {semi_pct:.1%} is high")
    if china_pct > 0.20:
        score += 4
        risks.append(f"China exposure {china_pct:.1%} is notable")
    score = min(score, 20)
    risk_level = _risk_level_from_score(score, 20)

    return SectorThemeExposureCard(
        summary=f"AI {ai_pct:.1%}, Semiconductor {semi_pct:.1%}, China {china_pct:.1%}, Mega-cap tech {mega_pct:.1%}.",
        score=round(score, 2), max_score=20, risk_level=risk_level,
        sector_exposures=theme_map,
        ai_exposure_pct=ai_pct, semiconductor_exposure_pct=semi_pct,
        china_exposure_pct=china_pct, mega_cap_tech_exposure_pct=mega_pct,
        key_risks=risks, evidence_quality="high",
    )


def _assess_stress_test(snapshot: dict) -> StressTestCard:
    """Deterministic stress test: what-if scenarios."""
    net_liq = snapshot.get("net_liquidation", 0) or 0
    positions = snapshot.get("positions", [])

    scenarios = []
    # Scenario 1: -10% market drop
    total_exposure = sum(
        (p.get("market_value", 0) if isinstance(p, dict) else 0)
        for p in positions
    )
    loss_10pct = total_exposure * 0.10
    scenarios.append({
        "name": "Market -10%",
        "assumed_drawdown": -0.10,
        "estimated_loss": round(loss_10pct, 2),
        "portfolio_impact_pct": round(loss_10pct / max(net_liq, 1) * 100, 2),
    })
    # Scenario 2: -20% market drop
    loss_20pct = total_exposure * 0.20
    scenarios.append({
        "name": "Market -20%",
        "assumed_drawdown": -0.20,
        "estimated_loss": round(loss_20pct, 2),
        "portfolio_impact_pct": round(loss_20pct / max(net_liq, 1) * 100, 2),
    })
    # Scenario 3: -30% single stock
    largest_value = max(
        (p.get("market_value", 0) if isinstance(p, dict) else 0)
        for p in positions
    ) if positions else 0
    loss_single = largest_value * 0.30
    scenarios.append({
        "name": "Largest position -30%",
        "assumed_drawdown": -0.30,
        "estimated_loss": round(loss_single, 2),
        "portfolio_impact_pct": round(loss_single / max(net_liq, 1) * 100, 2),
    })

    worst_case_pct = max(s["portfolio_impact_pct"] for s in scenarios) if scenarios else 0
    worst_case_loss = max(s["estimated_loss"] for s in scenarios) if scenarios else 0

    score = 0.0
    risks: list[str] = []
    if worst_case_pct > 20:
        score += 15
        risks.append(f"Worst-case scenario impact {worst_case_pct:.1f}% is significant")
    elif worst_case_pct > 10:
        score += 8
        risks.append(f"Worst-case scenario impact {worst_case_pct:.1f}%")
    score = min(score, 20)
    risk_level = _risk_level_from_score(score, 20)

    return StressTestCard(
        summary=f"Worst-case: {worst_case_pct:.1f}% portfolio impact, ${worst_case_loss:,.0f} loss.",
        score=round(score, 2), max_score=20, risk_level=risk_level,
        scenarios=scenarios,
        worst_case_drawdown_pct=worst_case_pct,
        worst_case_loss_amount=worst_case_loss,
        key_risks=risks, evidence_quality="high",
    )


def _build_composer_prompt(
    snapshot: dict, concentration: ConcentrationRiskCard,
    sector_theme: SectorThemeExposureCard, stress_test: StressTestCard,
) -> str:
    schema = {
        "overall_risk_score": 0, "risk_level": "medium", "summary": "...",
        "concentration_risk": {}, "sector_exposure": {}, "liquidity_risk": {},
        "stress_test": {}, "key_risks": [], "recommendations": [],
        "watch_points": [], "data_limitations": [], "evidence_used": [],
    }
    return (
        "Compose a portfolio risk assessment report.\n\n"
        f"Concentration card:\n{json.dumps(concentration.to_dict(), ensure_ascii=False, default=str)}\n\n"
        f"Sector/theme card:\n{json.dumps(sector_theme.to_dict(), ensure_ascii=False, default=str)}\n\n"
        f"Stress test card:\n{json.dumps(stress_test.to_dict(), ensure_ascii=False, default=str)}\n\n"
        f"Portfolio snapshot:\n{json.dumps(snapshot, ensure_ascii=False, default=str)}\n\n"
        f"Output strict JSON matching this schema:\n{json.dumps(schema, ensure_ascii=False)}\n"
    )


def _build_fallback_output(
    concentration: ConcentrationRiskCard,
    sector_theme: SectorThemeExposureCard,
    stress_test: StressTestCard,
) -> dict:
    total_score = concentration.score + sector_theme.score + stress_test.score
    return {
        "overall_risk_score": round(total_score, 2),
        "risk_level": "medium",
        "summary": f"Risk assessment generated with fallback. Concentration: {concentration.risk_level}, Sector: {sector_theme.risk_level}, Stress: {stress_test.risk_level}.",
        "concentration_risk": concentration.to_dict(),
        "sector_exposure": sector_theme.to_dict(),
        "liquidity_risk": {},
        "stress_test": stress_test.to_dict(),
        "key_risks": concentration.key_risks + sector_theme.key_risks + stress_test.key_risks,
        "recommendations": concentration.suggested_actions + sector_theme.suggested_actions,
        "watch_points": [],
        "data_limitations": ["LLM output validation failed; using deterministic fallback"],
        "evidence_used": ["deterministic concentration analysis", "deterministic sector/theme classification", "deterministic stress test"],
    }


def _risk_level_from_score(score: float, max_score: float) -> str:
    ratio = score / max_score if max_score > 0 else 0
    if ratio >= 0.75:
        return RiskLevel.EXTREME
    if ratio >= 0.50:
        return RiskLevel.HIGH
    if ratio >= 0.25:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _save_assessment(db: Any, document: dict) -> dict:
    if hasattr(db, "save_assessment"):
        return db.save_assessment(document)
    return document
