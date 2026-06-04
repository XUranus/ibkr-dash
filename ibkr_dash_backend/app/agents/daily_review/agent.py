"""Daily Position Review agent.

Simplified from the original LangGraph-based implementation.
Single async function that loads data, builds evidence, calls LLM, and saves.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.output_schemas import DailyPositionReviewOutput
from app.agents.prompt_runtime import resolve_runtime_prompt
from app.agents.daily_review.prompts import SYSTEM_PROMPT


async def generate_daily_review(
    db: Any,
    llm_service: Any,
    report_date: str,
    *,
    prompt_service: Any = None,
) -> dict:
    """Generate a daily position review report.

    1. Load account/position data from DB (deterministic)
    2. Select focus symbols
    3. Build evidence pack
    4. Call LLM with structured output
    5. Validate and save

    Args:
        db: Database session or repository.
        llm_service: LLM service for text generation.
        report_date: YYYY-MM-DD report date.
        prompt_service: Optional admin prompt override service.

    Returns:
        Saved review document dict.
    """
    from app.agents.evidence import build_daily_position_review_evidence_pack

    # Step 1: Load deterministic context from DB
    deterministic_context = _load_deterministic_context(db, report_date)
    overview = deterministic_context.get("overview", {})
    rankings = deterministic_context.get("rankings", {})
    risk = deterministic_context.get("risk", {})
    positions = deterministic_context.get("positions", [])
    focus_symbols = deterministic_context.get("focus_symbols", [])

    # Step 2: Build evidence pack
    evidence_pack = build_daily_position_review_evidence_pack({
        "report_date": report_date,
        "overview": overview,
        "rankings": rankings,
        "risk": risk,
        "benchmarks": deterministic_context.get("benchmarks", {}),
        "focus_symbols": focus_symbols,
        "symbol_public_context": deterministic_context.get("symbol_public_context", {}),
        "attribution_quality": deterministic_context.get("attribution_quality", {}),
        "data_quality": deterministic_context.get("data_quality", {}),
    })

    # Step 3: Build LLM prompt
    system_prompt, prompt_metadata = resolve_runtime_prompt(
        prompt_service, "daily_position_review_main", SYSTEM_PROMPT,
    )
    user_prompt = _build_user_prompt(report_date, overview, rankings, risk, focus_symbols, positions, evidence_pack)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Step 4: Call LLM with structured output
    from app.agents.structured_output import StructuredOutputContract, StructuredOutputRuntime

    contract = StructuredOutputContract(
        name="daily_position_review",
        agent_name="daily_position_review",
        node_name="compose",
        output_model=DailyPositionReviewOutput,
        schema_hint=DailyPositionReviewOutput.model_json_schema(),
        max_repair_attempts=1,
        repair_enabled=True,
        fallback_enabled=True,
        fallback_builder=lambda ctx, err, raw: _build_fallback_payload(report_date, overview, rankings, risk, focus_symbols),
    )
    so_runtime = StructuredOutputRuntime(llm_service)
    result = so_runtime.generate(messages, contract)

    if result.ok and result.payload:
        validated = _normalize_output(result.payload, report_date, deterministic_context)
    else:
        validated = _build_fallback_payload(report_date, overview, rankings, risk, focus_symbols)

    # Step 5: Save
    document = {
        **validated,
        "id": report_date,
        "review_type": "daily_position_review",
        "evidence_pack": evidence_pack,
        "raw_llm_response": result.raw_response if result.ok else "",
        "fallback_used": not result.ok,
        "prompt_metadata": {"daily_position_review_main": prompt_metadata},
    }
    saved = _save_review(db, document)
    return saved


def _load_deterministic_context(db: Any, report_date: str) -> dict:
    """Load deterministic account context from DB. Placeholder for real implementation."""
    # In production, this queries the review_service or repository
    if hasattr(db, "build_review_context"):
        return db.build_review_context(report_date, include_public_context=True, include_benchmarks=True)
    return {
        "overview": {},
        "rankings": {"profit_contributors": [], "loss_drags": [], "top_weights": []},
        "risk": {},
        "positions": [],
        "focus_symbols": [],
        "benchmarks": {},
        "symbol_public_context": {},
        "attribution_quality": {},
        "data_quality": {},
    }


def _build_user_prompt(
    report_date: str,
    overview: dict,
    rankings: dict,
    risk: dict,
    focus_symbols: list[str],
    positions: list[dict],
    evidence_pack: dict,
) -> str:
    """Build the user prompt with deterministic data."""
    schema = {
        "report_date": report_date,
        "summary": "One-line summary of today's account performance",
        "account_conclusion": "Today's account conclusion",
        "attribution_summary": "Account PnL attribution",
        "major_contributors_analysis": [{"symbol": "AMD.US", "analysis": "..."}],
        "major_drags_analysis": [{"symbol": "NVDA.US", "analysis": "..."}],
        "focus_symbol_analyses": [
            {
                "symbol": "AMD.US", "price_action": "...", "account_impact": "...",
                "possible_reasons": [], "valuation_note": "...", "cost_position_note": "...",
                "watch_points": [], "data_limitations": [],
            }
        ],
        "market_context": "Market and sector background",
        "risk_analysis": "Position risk changes",
        "tomorrow_watchlist": [
            {"symbol": "AMD.US", "reason": "...", "key_levels": [], "events": [], "conditions": []}
        ],
        "operation_observation": "Operation observation, not buy/sell advice",
        "data_limitations": [],
        "evidence_used": [],
    }

    daily_pnl = overview.get("daily_pnl", "N/A")
    daily_return = overview.get("daily_return_percent", "N/A")
    top_contributors = rankings.get("profit_contributors", [])[:3]
    top_drags = rankings.get("loss_drags", [])[:3]
    contributor_summary = ", ".join(item.get("symbol", "") for item in top_contributors) or "None"
    drag_summary = ", ".join(item.get("symbol", "") for item in top_drags) or "None"

    return (
        f"Generate a daily position review for {report_date}.\n\n"
        f"Account PnL: {daily_pnl}, Return: {daily_return}%\n"
        f"Top contributors: {contributor_summary}\n"
        f"Top drags: {drag_summary}\n"
        f"Focus symbols: {', '.join(focus_symbols[:6])}\n\n"
        f"Deterministic data is from IBKR. Do not modify these numbers.\n"
        f"Public explanations come from evidence. Do not fabricate public market facts.\n"
        f"Tomorrow's watchlist: observation conditions only, no buy/sell instructions.\n\n"
        f"Output strict JSON object matching this schema:\n{json.dumps(schema, ensure_ascii=False)}\n"
    )


def _normalize_output(payload: dict, report_date: str, deterministic_context: dict) -> dict:
    """Normalize and validate the LLM output."""
    model = DailyPositionReviewOutput.model_validate({**payload, "report_date": payload.get("report_date") or report_date})
    validated = model.model_dump()
    # Ensure report_date matches
    validated["report_date"] = report_date
    return validated


def _build_fallback_payload(
    report_date: str, overview: dict, rankings: dict, risk: dict, focus_symbols: list[str],
) -> dict:
    """Build fallback payload when LLM output fails validation."""
    top_contributors = rankings.get("profit_contributors", [])[:3]
    top_drags = rankings.get("loss_drags", [])[:3]
    contributor_symbols = ", ".join(item.get("symbol", "") for item in top_contributors) or "None"
    drag_symbols = ", ".join(item.get("symbol", "") for item in top_drags) or "None"
    daily_pnl = overview.get("daily_pnl", "N/A")
    daily_return = overview.get("daily_return_percent", "N/A")

    return {
        "report_date": report_date,
        "summary": f"Daily review generated with fallback. PnL: {daily_pnl}, Return: {daily_return}%.",
        "account_conclusion": f"Account PnL {daily_pnl}, return {daily_return}%. Contributors: {contributor_symbols}. Drags: {drag_symbols}.",
        "attribution_summary": f"Contributors: {contributor_symbols}. Drags: {drag_symbols}.",
        "major_contributors_analysis": [
            {"symbol": item.get("symbol"), "analysis": f"PnL {item.get('daily_pnl')}, contribution {item.get('contribution_ratio')}, weight {item.get('weight')}."}
            for item in top_contributors[:5]
        ],
        "major_drags_analysis": [
            {"symbol": item.get("symbol"), "analysis": f"PnL {item.get('daily_pnl')}, contribution {item.get('contribution_ratio')}, weight {item.get('weight')}."}
            for item in top_drags[:5]
        ],
        "focus_symbol_analyses": [
            {
                "symbol": symbol, "price_action": "LLM output format error; price explanation pending.",
                "account_impact": "See deterministic position contribution rankings below.",
                "possible_reasons": [], "valuation_note": "Public market explanation insufficient.",
                "cost_position_note": "See position details for cost and unrealized PnL.",
                "watch_points": ["Regenerate LLM review"], "data_limitations": ["LLM output was not valid JSON"],
            }
            for symbol in focus_symbols[:5]
        ],
        "market_context": "LLM output was not valid JSON; market explanation not generated.",
        "risk_analysis": "See deterministic risk data.",
        "tomorrow_watchlist": [
            {"symbol": symbol, "reason": "Key position or daily mover", "key_levels": [], "events": [], "conditions": ["Monitor volume and key moving averages"]}
            for symbol in focus_symbols[:5]
        ],
        "operation_observation": "Fallback review; no buy/sell conclusions. Regenerate when LLM output recovers.",
        "data_limitations": ["LLM output was not valid JSON; using deterministic fallback"],
        "evidence_used": ["deterministic IBKR data"],
    }


def _save_review(db: Any, document: dict) -> dict:
    """Save the review document to DB."""
    if hasattr(db, "save_review"):
        return db.save_review(document)
    return document
