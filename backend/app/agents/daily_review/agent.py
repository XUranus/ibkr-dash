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

# Longbridge benchmark symbols
BENCHMARK_SYMBOLS = ["SPY", "QQQ", "SMH"]

# Cache for Longbridge data to avoid repeated API calls within same request
_longbridge_cache: dict[str, Any] = {}
_longbridge_cache_date: str = ""


def _fetch_longbridge_context(
    focus_symbols: list[str],
    report_date: str,
) -> dict:
    """Fetch Longbridge public data for focus symbols and benchmarks.

    Returns:
        dict with 'symbol_public_context' and 'benchmarks' keys.
    """
    global _longbridge_cache, _longbridge_cache_date

    # Use cache if same date
    if _longbridge_cache_date == report_date and _longbridge_cache:
        return _longbridge_cache

    from app.core.config import get_settings
    from app.services.longbridge_service import LongbridgeExternalDataClient, LongbridgeUnavailableError

    settings = get_settings()
    client = LongbridgeExternalDataClient(settings)

    if not (client.enabled and client.configured and client.sdk_loaded):
        logger.info("Longbridge not available, skipping public context")
        return {"symbol_public_context": {}, "benchmarks": {"items": [], "beta_alpha_note": "Longbridge not available"}}

    symbol_public_context: dict[str, Any] = {}
    benchmarks: dict[str, Any] = {"items": [], "beta_alpha_note": ""}

    # 1. Fetch news for focus symbols (limit 5 per symbol)
    for symbol in focus_symbols[:6]:
        normalized = symbol.split(".")[0] if "." in symbol else symbol
        try:
            news_resp = client.get_news(symbol, limit=5)
            news_items = []
            if news_resp and news_resp.items:
                for item in news_resp.items[:5]:
                    news_items.append({
                        "title": getattr(item, "title", ""),
                        "summary": getattr(item, "summary", "")[:200],
                        "source": getattr(item, "source", ""),
                        "publish_time": str(getattr(item, "publish_time", "")),
                    })
            symbol_public_context[normalized] = {
                "symbol": symbol,
                "news": news_items,
                "news_count": len(news_items),
            }
        except (LongbridgeUnavailableError, Exception) as e:
            logger.warning("Failed to fetch news for %s: %s", symbol, str(e)[:100])
            symbol_public_context[normalized] = {"symbol": symbol, "news": [], "error": str(e)[:100]}

    # 2. Fetch benchmark candles (SPY, QQQ, SMH) for last 5 trading days
    try:
        from datetime import datetime, timedelta
        end_date = datetime.strptime(report_date, "%Y-%m-%d")
        start_date = end_date - timedelta(days=10)  # ~2 trading weeks

        benchmark_items = []
        for bm_symbol in BENCHMARK_SYMBOLS:
            try:
                candles_resp = client.get_candles(
                    bm_symbol,
                    start_date.strftime("%Y-%m-%d"),
                    report_date,
                    "day",
                    "forward",
                )
                if candles_resp and candles_resp.items:
                    # Get last 2 candles for return calculation
                    items = candles_resp.items
                    latest = items[-1] if items else None
                    prev = items[-2] if len(items) > 1 else None

                    if latest:
                        close_price = float(getattr(latest, "close", 0))
                        prev_close = float(getattr(prev, "close", 0)) if prev else 0
                        day_return = round((close_price - prev_close) / prev_close * 100, 2) if prev_close > 0 else 0

                        benchmark_items.append({
                            "symbol": bm_symbol,
                            "close": close_price,
                            "day_return_percent": day_return,
                            "candle_count": len(items),
                        })
            except (LongbridgeUnavailableError, Exception) as e:
                logger.warning("Failed to fetch candles for %s: %s", bm_symbol, str(e)[:100])

        benchmarks = {
            "items": benchmark_items,
            "beta_alpha_note": f"Benchmark returns from Longbridge ({len(benchmark_items)} symbols)",
        }
    except Exception as e:
        logger.warning("Failed to fetch benchmark data: %s", str(e)[:100])
        benchmarks = {"items": [], "beta_alpha_note": f"Benchmark fetch failed: {str(e)[:100]}"}

    result = {
        "symbol_public_context": symbol_public_context,
        "benchmarks": benchmarks,
    }

    # Update cache
    _longbridge_cache = result
    _longbridge_cache_date = report_date

    return result


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

    # Guard: skip if no account data at all
    data_quality = deterministic_context.get("data_quality", {})
    if data_quality.get("error"):
        logger.warning("DailyReview skipped: date=%s reason=%s", report_date, data_quality["error"])
        return {
            "report_date": report_date,
            "summary": "",
            "account_conclusion": "",
            "status": "skipped_no_data",
            "data_limitations": [data_quality["error"]],
        }
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
        fallback_builder=lambda ctx, err, raw: _build_fallback_payload(
            report_date, overview, rankings, risk, focus_symbols,
            symbol_public_context=deterministic_context.get("symbol_public_context"),
            benchmarks=deterministic_context.get("benchmarks"),
        ),
    )
    so_runtime = StructuredOutputRuntime(llm_service)
    result = so_runtime.generate(messages, contract)

    if result.ok and result.payload:
        validated = _normalize_output(result.payload, report_date, deterministic_context)
    else:
        validated = _build_fallback_payload(
            report_date, overview, rankings, risk, focus_symbols,
            symbol_public_context=deterministic_context.get("symbol_public_context"),
            benchmarks=deterministic_context.get("benchmarks"),
        )

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


# Module-level cache for ai_theme_role lookups (rarely changes)
_theme_role_cache: dict[str, str] = {}
_theme_role_cache_ts: float = 0.0
_THEME_ROLE_CACHE_TTL: float = 300.0  # 5 minutes


def _classify_theme_buckets(positions: list[dict], db: Any = None) -> list[dict]:
    """Classify positions into theme buckets.

    Priority:
    1. ``pm_universe_symbols.ai_theme_role`` from DB (when populated by AI agent)
    2. Description keyword matching (for uncategorized positions)
    """
    import time

    # Theme → ai_theme_role values that belong to it
    _ROLE_TO_THEME: dict[str, str] = {
        "semiconductor": "semiconductor",
        "semi_equipment": "semiconductor",
        "ai_chip": "semiconductor",
        "ai_infra": "ai",
        "ai_platform": "ai",
        "ai_application": "ai",
        "cloud": "ai",
        "china_adr": "china",
        "china_tech": "china",
    }

    # Description keyword fallback for positions not in pm_universe_symbols
    _DESC_KEYWORDS: dict[str, list[str]] = {
        "semiconductor": ["semiconductor", "chip", "foundry", "wafer", "fab"],
        "ai": ["artificial intelligence", "machine learning", "cloud computing", "data center"],
        "china": ["china", "chinese", "hong kong", "cayman", "sp adr"],
    }

    # Load ai_theme_role from DB with caching
    global _theme_role_cache, _theme_role_cache_ts
    now = time.time()
    if db is not None and (now - _theme_role_cache_ts > _THEME_ROLE_CACHE_TTL or not _theme_role_cache):
        try:
            rows = db.execute(
                "SELECT symbol, ai_theme_role FROM pm_universe_symbols "
                "WHERE ai_theme_role IS NOT NULL AND ai_theme_role != '' AND ai_theme_role != 'unknown'",
            )
            _theme_role_cache = {r["symbol"]: r["ai_theme_role"] for r in rows}
            _theme_role_cache_ts = now
        except Exception:
            pass
    role_map = _theme_role_cache

    # Build theme → symbols mapping
    theme_symbols: dict[str, list[str]] = {}
    for pos in positions:
        sym = pos.get("symbol", "")
        norm = pos.get("normalized_symbol") or sym
        desc = (pos.get("description") or "").lower()

        # 1. Check ai_theme_role from DB
        role = role_map.get(sym) or role_map.get(norm)
        if role and role in _ROLE_TO_THEME:
            theme = _ROLE_TO_THEME[role]
            theme_symbols.setdefault(theme, []).append(sym)
            continue

        # 2. Fallback: description keyword matching
        for theme, keywords in _DESC_KEYWORDS.items():
            if any(kw in desc for kw in keywords):
                theme_symbols.setdefault(theme, []).append(sym)
                break

    return [{"theme": t, "symbols": syms} for t, syms in theme_symbols.items() if syms]


def _load_deterministic_context(db: Any, report_date: str) -> dict:
    """Load deterministic account context from SQLite database."""
    # 1. Account snapshot — fall back to latest available date if requested date has no data
    account = db.execute_one(
        "SELECT * FROM account_snapshots WHERE report_date = ? LIMIT 1",
        (report_date,),
    )
    actual_date = report_date
    if not account:
        # Fallback: use the most recent available date
        latest = db.execute_one(
            "SELECT report_date FROM account_snapshots ORDER BY report_date DESC LIMIT 1",
        )
        if latest:
            actual_date = latest["report_date"]
            logger.info("DailyReview: no data for %s, falling back to latest date %s", report_date, actual_date)
            account = db.execute_one(
                "SELECT * FROM account_snapshots WHERE report_date = ? LIMIT 1",
                (actual_date,),
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
        (actual_date,),
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
        (actual_date,),
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

    # 4. Rankings: sort by daily PnL, excluding cash-like instruments
    from app.core.symbol_constants import CASH_EQUIVALENT_SYMBOLS
    equity_positions = [e for e in enriched if e["normalized_symbol"] not in CASH_EQUIVALENT_SYMBOLS]
    by_daily_pnl = sorted(equity_positions, key=lambda x: x["daily_pnl"], reverse=True)
    contributors = by_daily_pnl[:5]
    drags = by_daily_pnl[-5:] if len(by_daily_pnl) > 5 else []
    drags = list(reversed(drags))
    by_weight = sorted(enriched, key=lambda x: x["weight"], reverse=True)[:5]

    # Contribution ratio
    total_abs_pnl = sum(abs(e["daily_pnl"]) for e in equity_positions) or 1
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

    # Theme buckets — classified dynamically from DB ai_theme_role + description keywords
    theme_buckets = _classify_theme_buckets(enriched, db)
    semi_ai_symbols = set()
    for bucket in theme_buckets:
        if bucket["theme"] in ("semiconductor", "ai"):
            semi_ai_symbols.update(bucket["symbols"])
    semi_ai_weight = sum(e["weight"] for e in enriched if e["symbol"] in semi_ai_symbols)

    # Cash-like weight (add to effective cash ratio)
    cash_like_weight = sum(e["weight"] for e in enriched if e["normalized_symbol"] in CASH_EQUIVALENT_SYMBOLS)
    effective_cash_ratio = round(cash_ratio + cash_like_weight, 2)

    # Max position excluding cash-like instruments
    non_cash_positions = [e for e in enriched if e["normalized_symbol"] not in CASH_EQUIVALENT_SYMBOLS]
    max_pos_equity = non_cash_positions[0] if non_cash_positions else None

    risk = {
        "max_position": max_pos_equity,
        "max_single_position_weight": max_pos_equity["weight"] if max_pos_equity else 0,
        "top3_weight": round(top3_weight, 2),
        "top5_weight": round(top5_weight, 2),
        "theme_buckets": theme_buckets,
        "semiconductor_ai_tech_weight": round(semi_ai_weight, 2),
        "cash_ratio": round(cash_ratio, 2),
        "cash_like_weight": round(cash_like_weight, 2),
        "effective_cash_ratio": effective_cash_ratio,
        "risk_flags": [],
        "account_posture": "concentrated" if (max_pos_equity and max_pos_equity["weight"] > 25) else "balanced",
    }
    if max_pos_equity and max_pos_equity["weight"] > 25:
        risk["risk_flags"].append(f"最大持仓 {max_pos_equity['symbol']} 占比 {max_pos_equity['weight']:.1f}%，集中度偏高")
    if effective_cash_ratio < 5:
        risk["risk_flags"].append(f"现金缓冲偏低: {effective_cash_ratio:.1f}%（含现金等价物），流动性不足")
    elif cash_like_weight > 0:
        risk["risk_flags"].append(f"现金等价物（如短债ETF）占比 {cash_like_weight:.1f}%")

    # 6. Focus symbols: top contributors + drags + largest equity position (excluding cash-like)
    focus_set: set[str] = set()
    for e in contributors[:3]:
        focus_set.add(e["symbol"])
    for e in drags[:3]:
        focus_set.add(e["symbol"])
    if max_pos_equity:
        focus_set.add(max_pos_equity["symbol"])
    focus_symbols = list(focus_set)[:6]

    # 7. Overview
    stock_value = float(account.get("stock_value") or 0)
    if daily_pnl is not None:
        pnl_sign = "+" if daily_pnl >= 0 else ""
        summary_zh = f"总权益 ${total_equity:,.0f}，当日盈亏 {pnl_sign}${daily_pnl:,.0f}（{pnl_sign}{daily_return}%）"
    else:
        summary_zh = f"总权益 ${total_equity:,.0f}"
    overview = {
        "report_date": report_date,
        "currency": account.get("currency", "USD"),
        "total_equity": total_equity,
        "daily_pnl": daily_pnl,
        "daily_return_percent": daily_return,
        "total_position_value": total_position_value,
        "cash": cash,
        "cash_ratio": round(cash_ratio, 2),
        "effective_cash_ratio": effective_cash_ratio,
        "cash_like_weight": round(cash_like_weight, 2),
        "position_count": len(enriched),
        "top_contributors": contributors[:3],
        "top_drags": drags[:3],
        "summary": summary_zh,
        "ibkr_pnl_breakdown": {
            "realized": float(account.get("fifo_total_realized_pnl") or 0),
            "unrealized": float(account.get("fifo_total_unrealized_pnl") or 0),
            "cnav_mtm": float(account.get("cnav_mtm") or 0),
        },
    }

    # 8. Fetch Longbridge public context for focus symbols and benchmarks
    longbridge_ctx = _fetch_longbridge_context(focus_symbols, report_date)

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
        "benchmarks": longbridge_ctx.get("benchmarks", {"items": [], "beta_alpha_note": "Benchmark data not available."}),
        "symbol_public_context": longbridge_ctx.get("symbol_public_context", {}),
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
    symbol_public_context: dict | None = None, benchmarks: dict | None = None,
) -> dict:
    """Build fallback payload when LLM output fails validation.

    Uses deterministic IBKR data directly. No technical error messages
    are exposed to the user — all content reads as a normal review.
    """
    symbol_public_context = symbol_public_context or {}
    benchmarks = benchmarks or {}
    top_contributors = rankings.get("profit_contributors", [])[:3]
    top_drags = rankings.get("loss_drags", [])[:3]
    contributor_symbols = "、".join(item.get("symbol", "") for item in top_contributors if item.get("symbol")) or "暂无"
    drag_symbols = "、".join(item.get("symbol", "") for item in top_drags if item.get("symbol")) or "暂无"
    daily_pnl = overview.get("daily_pnl")
    daily_return = overview.get("daily_return_percent")
    total_equity = overview.get("total_equity", 0)
    cash_ratio = overview.get("cash_ratio", 0)
    position_count = overview.get("position_count", 0)

    # Build a human-readable P&L line
    if daily_pnl is not None:
        pnl_sign = "+" if daily_pnl >= 0 else ""
        pnl_line = f"当日盈亏 {pnl_sign}{daily_pnl:,.0f} 美元（{pnl_sign}{daily_return}%）"
    else:
        pnl_line = "当日盈亏数据不可用"

    equity_line = f"总权益 {total_equity:,.0f} 美元，现金占比 {cash_ratio}%，持仓 {position_count} 只"

    # Build contributor analysis with actual data
    def _build_position_analysis(item: dict, is_drag: bool = False) -> dict:
        symbol = item.get("symbol", "")
        pnl = item.get("daily_pnl", 0)
        weight = item.get("weight", 0)
        unrealized = item.get("unrealized_pnl", 0)
        change_pct = item.get("daily_change_percent", 0)

        parts = []
        if pnl:
            pnl_s = f"+{pnl:,.0f}" if pnl > 0 else f"{pnl:,.0f}"
            parts.append(f"当日估算盈亏 {pnl_s} 美元")
        if change_pct:
            chg_s = f"+{change_pct:.2f}%" if change_pct > 0 else f"{change_pct:.2f}%"
            parts.append(f"日内变动 {chg_s}")
        if weight:
            parts.append(f"仓位权重 {weight:.1f}%")
        if unrealized:
            unr_s = f"+{unrealized:,.0f}" if unrealized > 0 else f"{unrealized:,.0f}"
            parts.append(f"累计浮盈亏 {unr_s} 美元")

        analysis = "；".join(parts) if parts else f"仓位权重 {weight:.1f}%"
        return {"symbol": symbol, "analysis": analysis}

    # Build focus symbol analyses with position-specific context
    def _build_focus_analysis(symbol: str) -> dict:
        # Find the position data
        all_positions = (rankings.get("profit_contributors", []) or []) + (rankings.get("loss_drags", []) or []) + (rankings.get("top_weights", []) or [])
        pos = next((p for p in all_positions if p.get("symbol") == symbol), None)

        if pos:
            pnl = pos.get("daily_pnl", 0)
            weight = pos.get("weight", 0)
            unrealized = pos.get("unrealized_pnl", 0)
            asset_class = pos.get("asset_class", "")
            cost = pos.get("cost_basis", 0)
            market_val = pos.get("market_value", 0)

            impact_parts = []
            if pnl:
                impact_parts.append(f"当日{'贡献' if pnl > 0 else '拖累'} {abs(pnl):,.0f} 美元")
            if weight:
                impact_parts.append(f"权重 {weight:.1f}%")

            cost_parts = []
            if cost > 0 and market_val > 0:
                cost_parts.append(f"市值 {market_val:,.0f}，成本 {cost:,.0f}")
            if unrealized:
                unr_pct = (unrealized / cost * 100) if cost > 0 else 0
                cost_parts.append(f"浮盈亏 {unrealized:+,.0f}（{unr_pct:+.1f}%）")

            # Position-type-specific watch points
            watch = []
            if "OPT" in asset_class or "P00" in symbol or "C00" in symbol:
                watch.append("关注期权到期日和时间衰减")
                watch.append("标的股价与行权价的相对位置")
            elif weight and weight > 15:
                watch.append("仓位较重，关注集中度风险")
            else:
                watch.append("关注基本面变化和成交量")

            return {
                "symbol": symbol,
                "price_action": f"日内变动 {pos.get('daily_change_percent', 0):+.2f}%" if pos.get("daily_change_percent") else "日内变动数据不可用",
                "account_impact": "；".join(impact_parts) if impact_parts else "影响较小",
                "possible_reasons": [],
                "valuation_note": "、".join(cost_parts) if cost_parts else "成本数据不可用",
                "cost_position_note": f"权重 {weight:.1f}%" if weight else "",
                "watch_points": watch,
                "data_limitations": [],
            }

        return {
            "symbol": symbol,
            "price_action": "数据不可用",
            "account_impact": "重点持仓",
            "possible_reasons": [],
            "valuation_note": "",
            "cost_position_note": "",
            "watch_points": ["关注基本面变化"],
            "data_limitations": ["持仓数据不足"],
        }

    # Build differentiated watchlist
    def _build_watchlist_item(symbol: str) -> dict:
        all_positions = (rankings.get("profit_contributors", []) or []) + (rankings.get("loss_drags", []) or []) + (rankings.get("top_weights", []) or [])
        pos = next((p for p in all_positions if p.get("symbol") == symbol), None)
        asset_class = pos.get("asset_class", "") if pos else ""
        weight = pos.get("weight", 0) if pos else 0

        if "OPT" in asset_class or "P00" in symbol or "C00" in symbol:
            reason = "期权头寸，关注到期日和 Greeks 变化"
            conditions = ["标的股价是否突破关键价位", "隐含波动率变化"]
        elif weight and weight > 15:
            reason = "重仓标的，关注仓位变化"
            conditions = ["是否有重大消息面", "成交量是否异常"]
        else:
            reason = "重点持仓，继续观察"
            conditions = ["关注行业动态和财报日期"]

        return {"symbol": symbol, "reason": reason, "key_levels": [], "events": [], "conditions": conditions}

    # Risk analysis from deterministic data
    risk_flags = risk.get("risk_flags", [])
    risk_summary = "；".join(risk_flags) if risk_flags else "当前没有明显集中度警报"

    # Build market context from Longbridge benchmark data
    benchmark_items = benchmarks.get("items", [])
    if benchmark_items:
        bm_lines = []
        for bm in benchmark_items:
            ret = bm.get("day_return_percent", 0)
            ret_sign = "+" if ret >= 0 else ""
            bm_lines.append(f"{bm['symbol']} {ret_sign}{ret}%")
        market_context = f"基准指数：{'、'.join(bm_lines)}"
    else:
        market_context = "基准指数数据暂不可用"

    # Build news summaries for focus symbols from Longbridge
    def _build_focus_with_news(symbol: str) -> dict:
        base = _build_focus_analysis(symbol)
        # Add news from Longbridge
        norm = symbol.split(".")[0] if "." in symbol else symbol
        pub_ctx = symbol_public_context.get(norm, symbol_public_context.get(symbol, {}))
        news_items = pub_ctx.get("news", [])
        if news_items:
            news_titles = [n.get("title", "") for n in news_items[:3] if n.get("title")]
            if news_titles:
                base["possible_reasons"] = news_titles
                base["data_limitations"] = []
        return base

    # Evidence used
    evidence_used = ["IBKR 账户和持仓归因数据"]
    if benchmark_items:
        evidence_used.append(f"Longbridge 基准指数（{len(benchmark_items)} 个）")
    if symbol_public_context:
        evidence_used.append(f"Longbridge 新闻（{len(symbol_public_context)} 个标的）")

    return {
        "report_date": report_date,
        "summary": f"{pnl_line}。{equity_line}。",
        "account_conclusion": f"{pnl_line}。主要贡献来自 {contributor_symbols}，主要拖累来自 {drag_symbols}。",
        "attribution_summary": f"贡献者：{contributor_symbols}。拖累者：{drag_symbols}。",
        "major_contributors_analysis": [_build_position_analysis(item) for item in top_contributors[:5]],
        "major_drags_analysis": [_build_position_analysis(item, is_drag=True) for item in top_drags[:5]],
        "focus_symbol_analyses": [_build_focus_with_news(symbol) for symbol in focus_symbols[:5]],
        "market_context": market_context,
        "risk_analysis": risk_summary,
        "tomorrow_watchlist": [_build_watchlist_item(symbol) for symbol in focus_symbols[:5]],
        "operation_observation": "以上为确定性数据分析，不构成投资建议。",
        "data_limitations": ["LLM 分析暂不可用，本次使用确定性数据生成"],
        "evidence_used": evidence_used,
    }


def _generate_review_markdown(document: dict) -> str:
    """Generate unified Markdown content for daily review.

    This content is used for both web admin display and push notification.
    """
    lines = []

    # 1. Header with date
    report_date = document.get("report_date", "")
    lines.append(f"# 📊 每日复盘 | {report_date}")
    lines.append("")

    # 2. Summary
    summary = document.get("summary", "")
    if summary:
        lines.append(f"**{summary}**")
        lines.append("")

    # 3. Market context
    market = document.get("market_context", "")
    if market and "暂不可用" not in market:
        lines.append(f"## 📈 市场概况")
        lines.append(market)
        lines.append("")

    # 4. Major contributors
    contributors = document.get("major_contributors_analysis", [])
    if contributors:
        lines.append("## ✅ 主要贡献")
        for item in contributors[:5]:
            sym = item.get("symbol", "")
            analysis = item.get("analysis", "")
            if sym:
                lines.append(f"- **{sym}**: {analysis[:120]}")
        lines.append("")

    # 5. Major drags
    drags = document.get("major_drags_analysis", [])
    if drags:
        lines.append("## ❌ 主要拖累")
        for item in drags[:5]:
            sym = item.get("symbol", "")
            analysis = item.get("analysis", "")
            if sym:
                lines.append(f"- **{sym}**: {analysis[:120]}")
        lines.append("")

    # 6. Focus symbol analyses with news
    focus = document.get("focus_symbol_analyses", [])
    if focus:
        lines.append("## 🔍 重点标的")
        for fs in focus[:5]:
            symbol = fs.get("symbol", "")
            price = fs.get("price_action", "")
            impact = fs.get("account_impact", "")
            reasons = fs.get("possible_reasons", [])
            valuation = fs.get("valuation_note", "")

            lines.append(f"### {symbol}")
            if price:
                lines.append(f"- 价格: {price}")
            if impact:
                lines.append(f"- 账户影响: {impact[:100]}")
            if reasons:
                lines.append(f"- 动态: {'; '.join(r[:60] for r in reasons[:2])}")
            if valuation:
                lines.append(f"- 估值: {valuation[:100]}")
        lines.append("")

    # 7. Risk analysis
    risk = document.get("risk_analysis", "")
    if risk and "没有明显" not in risk and "当前没有明显" not in risk and len(risk) > 5:
        lines.append("## ⚠️ 风险提醒")
        lines.append(risk)
        lines.append("")

    # 8. Tomorrow watchlist
    watchlist = document.get("tomorrow_watchlist", [])
    if watchlist:
        lines.append("## 👁 明日关注")
        for item in watchlist[:5]:
            sym = item.get("symbol", "")
            reason = item.get("reason", "")
            if sym and reason:
                lines.append(f"- **{sym}**: {reason[:80]}")
        lines.append("")

    # 9. Operation observation
    operation = document.get("operation_observation", "")
    if operation:
        lines.append(f"*{operation}*")
        lines.append("")

    lines.append("---")
    lines.append("_以上为自动生成的复盘分析，不构成投资建议_")

    return "\n".join(lines)


def _save_review(db: Any, document: dict) -> dict:
    """Save the review document to SQLite database."""
    import json
    from uuid import uuid4
    review_id = document.get("id") or str(uuid4())
    review_output_zh = document.get("review_output_zh", {})

    # Generate unified Markdown content from Chinese translation if available
    if review_output_zh:
        # Merge Chinese translation with original document for markdown generation
        markdown_doc = {**document, **review_output_zh}
    else:
        markdown_doc = document
    review_markdown = _generate_review_markdown(markdown_doc)

    db.upsert("daily_position_reviews", {
        "id": review_id,
        "report_date": document.get("report_date", ""),
        "review_output": json.dumps(document, ensure_ascii=False, default=str),
        "review_output_zh": json.dumps(review_output_zh, ensure_ascii=False, default=str) if review_output_zh else None,
        "review_markdown": review_markdown,
        "metadata": json.dumps(document.get("metadata", {}), ensure_ascii=False, default=str),
        "evidence_summary": json.dumps(document.get("evidence_summary", {}), ensure_ascii=False, default=str),
        "run_trace": json.dumps(document.get("run_trace", []), ensure_ascii=False, default=str),
    }, conflict_cols=["id"])
    document["id"] = review_id
    document["review_markdown"] = review_markdown
    return document
