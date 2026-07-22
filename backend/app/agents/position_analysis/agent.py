"""Position Analysis agent — 7-dimension structured scoring.

Generates bilingual (Chinese + English) position analysis with
multi-dimensional scoring cards. Results are stored in the database
for frontend display.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.agents.position_analysis.prompts import (
    SYSTEM_PROMPT_EN,
    SYSTEM_PROMPT_ZH,
    build_user_prompt_en,
    build_user_prompt_zh,
)

logger = logging.getLogger(__name__)


def _fetch_longbridge_enrichment(positions: list[dict]) -> dict[str, dict]:
    """Fetch Longbridge valuation, forecast, and technical data for positions."""
    from app.core.config import get_settings
    from app.services.longbridge_service import LongbridgeExternalDataClient, LongbridgeUnavailableError

    settings = get_settings()
    client = LongbridgeExternalDataClient(settings)
    if not (client.enabled and client.configured and client.sdk_loaded):
        return {}

    enrichment: dict[str, dict] = {}
    for pos in positions[:15]:  # limit to top 15
        symbol = pos.get("symbol", "")
        if not symbol:
            continue
        data: dict[str, Any] = {}

        # 1. Valuation detail (PE, PB, PS, etc.)
        try:
            val = client.get_valuation_detail(symbol)
            if val:
                data["valuation"] = val
        except Exception:
            pass

        # 2. Analyst EPS forecast (target price, consensus)
        try:
            forecast = client.get_forecast_eps(symbol)
            if forecast:
                data["forecast"] = forecast
        except Exception:
            pass

        # 3. Calc indexes (technical indicators)
        try:
            calc = client.get_calc_indexes(symbol)
            if calc:
                data["calc_indexes"] = calc
        except Exception:
            pass

        # 4. Quote snapshot (current price, market cap)
        try:
            quote = client.get_quote_snapshot(symbol)
            if quote:
                data["quote"] = quote
        except Exception:
            pass

        if data:
            enrichment[symbol] = data

    return enrichment


def _build_fallback_score_detail(positions: list[dict], account_data: dict, enrichment: dict | None = None) -> dict:
    """Build deterministic fallback score detail when LLM is unavailable."""
    total_equity = account_data.get("total_equity", 0) or 1
    cash = account_data.get("cash", 0) or 0
    cash_ratio = cash / total_equity * 100 if total_equity > 0 else 0

    # Count positions
    position_count = len(positions)
    weights = [float(p.get("percent_of_nav") or 0) for p in positions]
    max_weight = max(weights) if weights else 0
    top3_weight = sum(sorted(weights, reverse=True)[:3])

    # Average daily change
    changes = [float(p.get("previous_day_change_percent") or 0) for p in positions]
    avg_change = sum(changes) / len(changes) if changes else 0

    # Average unrealized PnL
    upnls = [float(p.get("total_unrealized_pnl") or 0) for p in positions]
    total_upnl = sum(upnls)
    avg_upnl = total_upnl / len(upnls) if upnls else 0

    # Cash-like detection
    cash_like = {"SHV", "BIL", "SGOV", "ICSH", "SHY", "MINT", "NEAR", "JPST", "GSY", "BOXX", "USFR", "TFLO", "STRC"}
    cash_like_weight = sum(float(p.get("percent_of_nav") or 0) for p in positions
                          if p.get("symbol", "").split(".")[0].upper() in cash_like)

    # Calculate effective cash ratio (cash + cash-like instruments like SHV)
    effective_cash_ratio = round(cash_ratio + cash_like_weight, 2)

    scores = {}

    # 1. Company quality — based on position count and description quality
    has_descriptions = sum(1 for p in positions if p.get("description"))
    desc_ratio = has_descriptions / position_count if position_count else 0
    scores["company_quality"] = {
        "score": min(20, int(10 + desc_ratio * 5 + (1 if position_count > 5 else 0) * 5)),
        "max_score": 20,
        "reason": f"持仓{position_count}只，{has_descriptions}只有描述数据",
    }

    # 2. Valuation quality — can't determine without market data, conservative
    scores["valuation_quality"] = {
        "score": 8,
        "max_score": 15,
        "reason": "缺少实时估值数据，按中性评估",
    }

    # 3. Trend strength — based on average daily change
    if avg_change > 1:
        trend_score = 12
        trend_reason = f"平均日涨幅 {avg_change:+.2f}%，趋势偏强"
    elif avg_change > 0:
        trend_score = 10
        trend_reason = f"平均日涨幅 {avg_change:+.2f}%，趋势中性偏强"
    elif avg_change > -1:
        trend_score = 7
        trend_reason = f"平均日涨幅 {avg_change:+.2f}%，趋势中性偏弱"
    else:
        trend_score = 4
        trend_reason = f"平均日涨幅 {avg_change:+.2f}%，趋势偏弱"
    scores["trend_strength"] = {"score": trend_score, "max_score": 15, "reason": trend_reason}

    # 4. Account fit — based on concentration and effective cash ratio (including cash-like)
    if max_weight > 25:
        fit_score = 8
        fit_reason = f"最大持仓占比 {max_weight:.1f}%，集中度偏高"
    elif effective_cash_ratio < 5:
        fit_score = 10
        fit_reason = f"有效现金比例 {effective_cash_ratio:.1f}%（含现金等价物），流动性偏低"
    elif cash_like_weight > 40:
        fit_score = 12
        fit_reason = f"现金等价物占比 {cash_like_weight:.1f}%，仓位偏保守"
    else:
        fit_score = 14
        fit_reason = f"仓位分布较均衡，有效现金比例 {effective_cash_ratio:.1f}%"
    scores["account_fit"] = {"score": fit_score, "max_score": 20, "reason": fit_reason}

    # 5. Risk/reward — based on unrealized PnL
    if total_upnl > 0:
        rr_score = 11
        rr_reason = f"总浮盈 {total_upnl:+,.0f} 美元，风险收益尚可"
    elif total_upnl > -1000:
        rr_score = 8
        rr_reason = f"总浮亏 {total_upnl:+,.0f} 美元，风险收益一般"
    else:
        rr_score = 5
        rr_reason = f"总浮亏 {total_upnl:+,.0f} 美元，风险收益较差"
    scores["risk_reward"] = {"score": rr_score, "max_score": 15, "reason": rr_reason}

    # 6. Review constraints
    scores["review_constraints"] = {
        "score": 8,
        "max_score": 10,
        "reason": "无复盘警告",
    }

    # 7. Event catalyst — can't determine without news data
    scores["event_catalyst"] = {
        "score": 3,
        "max_score": 5,
        "reason": "缺少事件数据，按中等催化评估",
    }

    overall = sum(s["score"] for s in scores.values())

    # Rating
    if overall >= 85:
        rating = "excellent"
    elif overall >= 70:
        rating = "good"
    elif overall >= 50:
        rating = "fair"
    else:
        rating = "poor"

    # Build position advice based on effective cash ratio
    if max_weight > 20 and cash_like_weight < 30:
        advice_action = "reduce"
        advice_rationale = f"最大持仓占比 {max_weight:.1f}%，建议降低集中度"
    elif effective_cash_ratio < 5:
        advice_action = "hold"
        advice_rationale = f"有效现金比例偏低（{effective_cash_ratio:.1f}%），建议保持现有仓位"
    else:
        advice_action = "hold"
        advice_rationale = f"仓位分布合理，有效现金比例 {effective_cash_ratio:.1f}%（含现金等价物），建议维持当前策略"

    # Build key risks
    key_risks = []
    if max_weight > 20 and cash_like_weight < 30:
        key_risks.append(f"集中度风险：最大持仓权重达 {max_weight:.1f}%")
    if effective_cash_ratio < 5:
        key_risks.append(f"流动性风险：有效现金比例仅 {effective_cash_ratio:.1f}%（含现金等价物）")
    if total_upnl < 0:
        key_risks.append(f"浮亏风险：未实现亏损 {total_upnl:+,.0f} 美元")

    # Build strengths and weaknesses
    strengths = []
    weaknesses = []
    if position_count > 10:
        strengths.append(f"持仓分散（{position_count}只），降低单一标的风险")
    if cash_like_weight > 20:
        strengths.append(f"现金等价物（如SHV）占比 {cash_like_weight:.1f}%，流动性充足")
    if total_upnl > 0:
        strengths.append(f"整体浮盈 {total_upnl:+,.0f} 美元")
    if max_weight > 20 and cash_like_weight < 30:
        weaknesses.append(f"最大持仓占比 {max_weight:.1f}%，集中度偏高")
    if effective_cash_ratio < 5:
        weaknesses.append(f"有效现金比例仅 {effective_cash_ratio:.1f}%，流动性不足")

    return {
        "overall_score": overall,
        "rating": rating,
        "summary": f"持仓{position_count}只，总权益${total_equity:,.0f}，有效现金比例{effective_cash_ratio:.1f}%（含现金等价物），综合评分{overall}分。",
        "score_detail": scores,
        "position_advice": {
            "action": advice_action,
            "target_pct": round(100 / position_count, 1) if position_count > 0 else 0,
            "max_pct": 20,
            "rationale": advice_rationale,
            "urgency": "medium" if max_weight > 20 else "low",
        },
        "strengths": strengths,
        "weaknesses": weaknesses,
        "key_risks": key_risks,
        "data_limitations": ["LLM 不可用，使用确定性数据生成评分"],
    }


def _parse_llm_json(text: str) -> dict | None:
    """Extract JSON from LLM response, handling markdown code blocks."""
    if not text:
        return None
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from code block
    import re
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None


async def generate_position_analysis(
    db: Any,
    llm_service: Any,
    report_date: str,
) -> dict | None:
    """Generate a 7-dimension position analysis report.

    1. Load account + position data from DB
    2. Call LLM for structured JSON scoring (ZH)
    3. Parse and validate
    4. Save to DB

    Returns:
        Saved document dict, or None if data unavailable.
    """
    logger.info("Starting position analysis for %s", report_date)

    # Step 1: Load data
    account = db.execute_one(
        "SELECT * FROM account_snapshots ORDER BY report_date DESC LIMIT 1"
    )
    if not account:
        logger.warning("No account data found, skipping analysis")
        return None

    effective_date = report_date or account.get("report_date", "")
    positions = db.execute(
        """
        SELECT symbol, description, asset_class, quantity, mark_price,
               position_value, percent_of_nav, previous_day_change_percent,
               total_unrealized_pnl, total_realized_pnl, average_cost_price,
               cost_basis_money
        FROM position_snapshots
        WHERE report_date = ?
        ORDER BY position_value DESC
        """,
        (effective_date,),
    )

    if not positions:
        logger.warning("No positions found for %s", effective_date)
        return None

    account_data = {
        "total_equity": float(account.get("total_equity") or 0),
        "cash": float(account.get("cash") or 0),
        "stock_value": float(account.get("stock_value") or 0),
        "report_date": effective_date,
    }

    # Step 1.5: Enrich with Longbridge public data
    enrichment_data = _fetch_longbridge_enrichment(positions)
    if enrichment_data:
        logger.info("Longbridge enrichment loaded for %d symbols", len(enrichment_data))

    # Step 2: Try LLM scoring
    scored = None
    if llm_service and getattr(llm_service, 'api_key', None):
        prompt_zh = build_user_prompt_zh(account_data, positions, enrichment_data)
        messages_zh = [
            {"role": "system", "content": SYSTEM_PROMPT_ZH},
            {"role": "user", "content": prompt_zh},
        ]
        try:
            response_zh = llm_service.chat(messages_zh, timeout=120)
            scored = _parse_llm_json(response_zh)
            if scored:
                logger.info("LLM scoring completed: overall=%s", scored.get("overall_score"))
        except Exception as exc:
            logger.warning("LLM scoring failed: %s", exc)

    # Step 3: Fallback if LLM failed
    if not scored or "score_detail" not in scored:
        scored = _build_fallback_score_detail(positions, account_data, enrichment_data)
        scored["data_limitations"] = scored.get("data_limitations", []) + ["使用确定性数据生成评分"]

    # Step 4: Save to DB
    analysis_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    db.upsert("position_analysis", {
        "id": analysis_id,
        "report_date": effective_date,
        "analysis_zh": json.dumps(scored, ensure_ascii=False),
        "analysis_en": json.dumps(scored, ensure_ascii=False),  # Same data, frontend handles display
        "created_at": now,
    }, conflict_cols=["id"])

    logger.info("Saved position analysis %s for %s (score=%s)", analysis_id, effective_date, scored.get("overall_score"))

    # Step 5: Push notification
    try:
        from app.services.notification_service import notify_position_analysis_completed
        notify_position_analysis_completed({
            "report_date": effective_date,
            **scored,
        })
    except Exception:
        logger.debug("PositionAnalysis notification skipped", exc_info=True)

    return {
        "id": analysis_id,
        "report_date": effective_date,
        **scored,
        "created_at": now,
    }
