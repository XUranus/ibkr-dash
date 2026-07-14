"""Daily Position Review agent.

Simplified from the original LangGraph-based implementation.
Single async function that loads data, builds evidence, calls LLM, and saves.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.agents.output_schemas import DailyPositionReviewOutput
from app.agents.prompt_runtime import resolve_runtime_prompt
from app.agents.daily_review.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


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
    logger.info("DailyReview started: date=%s", report_date)
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

    # Step 5: Translate to Chinese
    review_output_zh = {}
    try:
        from app.services.translation_service import translate_daily_review_output
        import time as _time
        _t0 = _time.monotonic()
        loop2 = asyncio.get_running_loop()
        review_output_zh = await loop2.run_in_executor(
            None, translate_daily_review_output, llm_service, validated, "English", "Chinese",
        )
        logger.info("DailyReview translation completed: duration_ms=%d fields=%d", int((_time.monotonic() - _t0) * 1000), len(review_output_zh) if review_output_zh else 0)
    except Exception:
        logger.debug("DailyReview translation skipped", exc_info=True)

    # Step 6: Save
    document = {
        **validated,
        "id": report_date,
        "review_type": "daily_position_review",
        "evidence_pack": evidence_pack,
        "raw_llm_response": result.raw_response if result.ok else "",
        "fallback_used": not result.ok,
        "run_trace": result.trace if hasattr(result, "trace") else [],
        "prompt_metadata": {"daily_position_review_main": prompt_metadata},
        "review_output_zh": review_output_zh,
    }
    saved = _save_review(db, document)
    logger.info("DailyReview completed: date=%s status=%s", report_date, saved.get("status", "ok"))
    # Push notification
    try:
        from app.services.notification_service import notify_daily_review_completed
        notify_daily_review_completed(saved)
    except Exception:
        logger.debug("DailyReview notification skipped", exc_info=True)
    return saved


def _load_deterministic_context(db: Any, report_date: str) -> dict:
    """Load deterministic account context from SQLite database."""
    # 1. Account snapshot
    account = db.execute_one(
        "SELECT * FROM account_snapshots WHERE report_date = ? LIMIT 1",
        (report_date,),
    )
    if not account:
        return {
            "overview": {},
            "rankings": {"profit_contributors": [], "loss_drags": [], "top_weights": []},
            "risk": {},
            "positions": [],
            "focus_symbols": [],
            "benchmarks": {},
            "symbol_public_context": {},
            "attribution_quality": {},
            "data_quality": {"error": f"No account data for {report_date}"},
        }

    total_equity = float(account.get("total_equity") or 0)
    cash = float(account.get("cash") or 0)

    # 2. Previous day snapshot for daily PnL
    prev_account = db.execute_one(
        "SELECT total_equity FROM account_snapshots WHERE report_date < ? ORDER BY report_date DESC LIMIT 1",
        (report_date,),
    )
    prev_equity = float(prev_account["total_equity"]) if prev_account else 0
    daily_pnl = round(total_equity - prev_equity, 2) if prev_equity > 0 else None
    daily_return = round((daily_pnl / prev_equity) * 100, 4) if prev_equity > 0 and daily_pnl is not None else None

    # 3. Positions
    positions = db.execute(
        "SELECT symbol, description, asset_class, quantity, mark_price, position_value, "
        "percent_of_nav, average_cost_price, cost_basis_money, "
        "fifo_pnl_unrealized, total_unrealized_pnl, total_realized_pnl, "
        "previous_day_change_percent "
        "FROM position_snapshots WHERE report_date = ? ORDER BY position_value DESC",
        (report_date,),
    )

    # Enrich positions with computed fields
    total_position_value = sum(abs(float(p.get("position_value") or 0)) for p in positions)
    enriched = []
    for p in positions:
        pos_val = float(p.get("position_value") or 0)
        weight = (pos_val / total_equity * 100) if total_equity > 0 else 0
        daily_chg = float(p.get("previous_day_change_percent") or 0)
        # Estimate daily PnL from position value and daily change
        daily_pnl_est = round(pos_val * daily_chg / 100, 2) if daily_chg else 0
        enriched.append({
            **p,
            "normalized_symbol": p.get("symbol", "").split(".")[0],
            "weight": round(weight, 2),
            "daily_change_percent": daily_chg,
            "daily_pnl": daily_pnl_est,
            "market_value": pos_val,
            "unrealized_pnl": float(p.get("fifo_pnl_unrealized") or p.get("total_unrealized_pnl") or 0),
            "unrealized_pnl_percent": 0,
            "cost_basis": float(p.get("cost_basis_money") or 0),
            "average_cost": float(p.get("average_cost_price") or 0),
            "contribution_ratio": 0,
            "is_major_contributor": False,
            "is_major_drag": False,
            "data_source": "ibkr",
        })

    # Compute unrealized PnL percent
    for e in enriched:
        cost = e["cost_basis"]
        if cost > 0:
            e["unrealized_pnl_percent"] = round((e["unrealized_pnl"] / cost) * 100, 2)

    # 4. Rankings: sort by daily PnL
    by_daily_pnl = sorted(enriched, key=lambda x: x["daily_pnl"], reverse=True)
    contributors = by_daily_pnl[:5]
    drags = by_daily_pnl[-5:] if len(by_daily_pnl) > 5 else []
    drags = list(reversed(drags))
    by_weight = sorted(enriched, key=lambda x: x["weight"], reverse=True)[:5]

    # Contribution ratio
    total_abs_pnl = sum(abs(e["daily_pnl"]) for e in enriched) or 1
    for e in contributors:
        e["contribution_ratio"] = round(e["daily_pnl"] / total_abs_pnl * 100, 2)
        e["is_major_contributor"] = True
    for e in drags:
        e["contribution_ratio"] = round(e["daily_pnl"] / total_abs_pnl * 100, 2)
        e["is_major_drag"] = True

    # 5. Risk metrics
    weights = [e["weight"] for e in enriched]
    max_pos = enriched[0] if enriched else None
    top3_weight = sum(sorted(weights, reverse=True)[:3])
    top5_weight = sum(sorted(weights, reverse=True)[:5])
    cash_ratio = (cash / total_equity * 100) if total_equity > 0 else 0

    # Theme buckets (simple classification)
    semi_keywords = {"NVDA", "AMD", "TSM", "AVGO", "QCOM", "MU", "INTC", "MRVL", "ARM", "ASML"}
    ai_keywords = {"NVDA", "MSFT", "GOOG", "GOOGL", "META", "AMZN", "CRM", "PLTR"}
    china_keywords = {"BABA", "JD", "PDD", "NIO", "XPEV", "LI", "BIDU", "TME"}
    theme_buckets = [
        {"theme": "semiconductor", "symbols": [e["symbol"] for e in enriched if e["normalized_symbol"] in semi_keywords]},
        {"theme": "ai", "symbols": [e["symbol"] for e in enriched if e["normalized_symbol"] in ai_keywords]},
        {"theme": "china", "symbols": [e["symbol"] for e in enriched if e["normalized_symbol"] in china_keywords]},
    ]
    semi_ai_weight = sum(e["weight"] for e in enriched if e["normalized_symbol"] in semi_keywords | ai_keywords)

    risk = {
        "max_position": max_pos,
        "max_single_position_weight": max_pos["weight"] if max_pos else 0,
        "top3_weight": round(top3_weight, 2),
        "top5_weight": round(top5_weight, 2),
        "theme_buckets": theme_buckets,
        "semiconductor_ai_tech_weight": round(semi_ai_weight, 2),
        "cash_ratio": round(cash_ratio, 2),
        "risk_flags": [],
        "account_posture": "concentrated" if (max_pos and max_pos["weight"] > 25) else "balanced",
    }
    if max_pos and max_pos["weight"] > 25:
        risk["risk_flags"].append(f"Top position {max_pos['symbol']} at {max_pos['weight']:.1f}%")
    if cash_ratio < 5:
        risk["risk_flags"].append(f"Low cash buffer: {cash_ratio:.1f}%")

    # 6. Focus symbols: top contributors + drags + largest position
    focus_set: set[str] = set()
    for e in contributors[:3]:
        focus_set.add(e["symbol"])
    for e in drags[:3]:
        focus_set.add(e["symbol"])
    if max_pos:
        focus_set.add(max_pos["symbol"])
    focus_symbols = list(focus_set)[:6]

    # 7. Overview
    stock_value = float(account.get("stock_value") or 0)
    overview = {
        "report_date": report_date,
        "currency": account.get("currency", "USD"),
        "total_equity": total_equity,
        "daily_pnl": daily_pnl,
        "daily_return_percent": daily_return,
        "total_position_value": total_position_value,
        "cash": cash,
        "cash_ratio": round(cash_ratio, 2),
        "position_count": len(enriched),
        "top_contributors": contributors[:3],
        "top_drags": drags[:3],
        "summary": f"Equity ${total_equity:,.0f}, PnL ${daily_pnl:,.0f} ({daily_return}%)" if daily_pnl is not None else f"Equity ${total_equity:,.0f}",
        "ibkr_pnl_breakdown": {
            "realized": float(account.get("fifo_total_realized_pnl") or 0),
            "unrealized": float(account.get("fifo_total_unrealized_pnl") or 0),
            "cnav_mtm": float(account.get("cnav_mtm") or 0),
        },
    }

    return {
        "overview": overview,
        "rankings": {
            "profit_contributors": contributors,
            "loss_drags": drags,
            "top_weights": by_weight,
        },
        "risk": risk,
        "positions": enriched,
        "focus_symbols": focus_symbols,
        "benchmarks": {"items": [], "beta_alpha_note": "Benchmark data not available."},
        "symbol_public_context": {},
        "attribution_quality": {
            "has_daily_change": any(e["daily_change_percent"] != 0 for e in enriched),
            "has_pnl_data": daily_pnl is not None,
        },
        "data_quality": {
            "positions_count": len(enriched),
            "has_account_data": True,
            "has_previous_day": prev_equity > 0,
        },
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
    """Save the review document to SQLite database."""
    import json
    from uuid import uuid4
    review_id = document.get("id") or str(uuid4())
    review_output_zh = document.pop("review_output_zh", {})
    db.upsert("daily_position_reviews", {
        "id": review_id,
        "report_date": document.get("report_date", ""),
        "review_output": json.dumps(document, ensure_ascii=False, default=str),
        "review_output_zh": json.dumps(review_output_zh, ensure_ascii=False, default=str) if review_output_zh else None,
        "metadata": json.dumps(document.get("metadata", {}), ensure_ascii=False, default=str),
        "evidence_summary": json.dumps(document.get("evidence_summary", {}), ensure_ascii=False, default=str),
        "run_trace": json.dumps(document.get("run_trace", []), ensure_ascii=False, default=str),
    }, conflict_cols=["id"])
    document["id"] = review_id
    return document
