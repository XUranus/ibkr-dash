"""Business notification service.

Sends push notifications for key business events via NotifyHub.
Each function is safe to call — it silently no-ops if NotifyHub is not configured.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _send(subject: str, body: str, **kwargs: Any) -> None:
    """Send notification, swallowing all errors."""
    try:
        from app.services.notifyhub_service import is_configured, send_notification
        if not is_configured():
            return
        result = send_notification(subject, body, **kwargs)
        if not result.success:
            logger.warning("Notification failed: %s", result.message)
    except Exception as exc:
        logger.warning("Notification error: %s", exc)


# ---------------------------------------------------------------------------
# 每日持仓复盘
# ---------------------------------------------------------------------------

def _get_language() -> str:
    """Get configured notification language."""
    try:
        from app.core.settings_manager import get_manager
        return str(get_manager().get("notifyhub.language", "zh"))
    except Exception:
        return "zh"


def _pick(document: dict, field: str, fallback: str = "") -> str:
    """Pick field value: prefer zh if configured, fallback to en."""
    lang = _get_language()
    if lang == "zh":
        zh = document.get("review_output_zh", {})
        if isinstance(zh, dict) and zh.get(field):
            return str(zh[field])
    return str(document.get(field, fallback))


def notify_daily_review_completed(document: dict) -> None:
    """每日复盘完成推送 — 发送完整报告."""
    report_date = document.get("report_date", "")
    subject = f"📊 每日持仓复盘 | {report_date}"

    sections = []

    # 1. 摘要与结论
    summary = _pick(document, "summary")
    conclusion = _pick(document, "account_conclusion")
    if summary:
        sections.append(f"## 摘要\n\n{summary}")
    if conclusion:
        sections.append(f"## 账户结论\n\n{conclusion}")

    # 2. 归因分析
    attribution = _pick(document, "attribution_summary")
    if attribution:
        sections.append(f"## 归因分析\n\n{attribution}")

    # 3. 主要贡献者
    contributors = _pick_list(document, "major_contributors_analysis")
    if contributors:
        lines = []
        for item in contributors:
            symbol = item.get("symbol", "")
            analysis = item.get("analysis", "")
            if symbol and analysis:
                lines.append(f"- **{symbol}**: {analysis}")
        if lines:
            sections.append("## 主要贡献者\n\n" + "\n".join(lines))

    # 4. 主要拖累
    drags = _pick_list(document, "major_drags_analysis")
    if drags:
        lines = []
        for item in drags:
            symbol = item.get("symbol", "")
            analysis = item.get("analysis", "")
            if symbol and analysis:
                lines.append(f"- **{symbol}**: {analysis}")
        if lines:
            sections.append("## 主要拖累\n\n" + "\n".join(lines))

    # 5. 重点标的分析
    focus = _pick_list(document, "focus_symbol_analyses")
    if focus:
        lines = []
        for item in focus:
            symbol = item.get("symbol", "")
            parts = []
            if item.get("price_action"):
                parts.append(f"**走势**: {item['price_action']}")
            if item.get("account_impact"):
                parts.append(f"**账户影响**: {item['account_impact']}")
            if item.get("possible_reasons"):
                reasons = "; ".join(item["possible_reasons"][:3])
                parts.append(f"**可能原因**: {reasons}")
            if item.get("valuation_note"):
                parts.append(f"**估值**: {item['valuation_note']}")
            if item.get("cost_position_note"):
                parts.append(f"**成本仓位**: {item['cost_position_note']}")
            if item.get("watch_points"):
                watch = "; ".join(item["watch_points"][:3])
                parts.append(f"**关注点**: {watch}")
            if symbol and parts:
                lines.append(f"### {symbol}\n\n" + "\n\n".join(parts))
        if lines:
            sections.append("## 重点标的分析\n\n" + "\n\n".join(lines))

    # 6. 市场背景
    market = _pick(document, "market_context")
    if market:
        sections.append(f"## 市场背景\n\n{market}")

    # 7. 风险分析
    risk = _pick(document, "risk_analysis")
    if risk:
        sections.append(f"## 风险分析\n\n{risk}")

    # 8. 明日关注
    watchlist = _pick_list(document, "tomorrow_watchlist")
    if watchlist:
        lines = []
        for item in watchlist:
            symbol = item.get("symbol", "")
            reason = item.get("reason", "")
            conditions = item.get("conditions", [])
            parts = []
            if reason:
                parts.append(reason)
            if conditions:
                parts.append("条件: " + "; ".join(conditions[:3]))
            if symbol and parts:
                lines.append(f"- **{symbol}**: {' | '.join(parts)}")
        if lines:
            sections.append("## 明日关注\n\n" + "\n".join(lines))

    # 9. 操作观察
    ops = _pick(document, "operation_observation")
    if ops:
        sections.append(f"## 操作观察\n\n{ops}")

    # 10. 数据限制
    limitations = _pick_list(document, "data_limitations")
    if limitations:
        sections.append("## 数据限制\n\n" + "\n".join(f"- {item}" for item in limitations if item))

    body = "\n\n".join(sections) if sections else "复盘报告已生成，请查看详细内容。"

    _send(subject, body)


def _pick_list(document: dict, field: str) -> list:
    """Pick list field: prefer zh if configured, fallback to en."""
    lang = _get_language()
    if lang == "zh":
        zh = document.get("review_output_zh", {})
        if isinstance(zh, dict) and zh.get(field):
            val = zh[field]
            return val if isinstance(val, list) else []
    val = document.get(field, [])
    return val if isinstance(val, list) else []


def notify_daily_review_failed(report_date: str, reason: str) -> None:
    """每日复盘失败推送."""
    subject = f"⚠️ 每日复盘失败 | {report_date}"
    body = f"**原因:** {reason[:300]}"

    _send(subject, body)


# ---------------------------------------------------------------------------
# 交易复盘
# ---------------------------------------------------------------------------

def notify_trade_review_completed(document: dict) -> None:
    """交易复盘完成推送."""
    symbol = document.get("symbol", "")
    trade_id = document.get("trade_id", "")
    overall_score = document.get("overall_score", "")
    summary = document.get("summary", "")

    subject = f"📝 交易复盘完成 | {symbol}"

    lines = []
    if trade_id:
        lines.append(f"**交易ID:** {trade_id}")
    if overall_score:
        lines.append(f"**评分:** {overall_score}")
    if summary:
        lines.append(f"**摘要:** {summary[:300]}")
    body = "\n\n".join(lines) if lines else "交易复盘已生成，请查看详细报告。"

    _send(subject, body)


def notify_trade_review_failed(symbol: str, reason: str) -> None:
    """交易复盘失败推送."""
    subject = f"⚠️ 交易复盘失败 | {symbol}"
    body = f"**原因:** {reason[:300]}"

    _send(subject, body)


# ---------------------------------------------------------------------------
# AI 交易决策
# ---------------------------------------------------------------------------

def notify_trade_decision_completed(document: dict) -> None:
    """交易决策完成推送."""
    symbol = document.get("symbol", "")
    decision = document.get("decision", {})
    action = decision.get("action", "") if isinstance(decision, dict) else ""
    conviction = decision.get("conviction", "") if isinstance(decision, dict) else ""

    subject = f"🤖 AI 决策完成 | {symbol}"

    lines = []
    if action:
        lines.append(f"**建议操作:** {action}")
    if conviction:
        lines.append(f"**确信度:** {conviction}")

    key_reasons = decision.get("key_reasons", []) if isinstance(decision, dict) else []
    if key_reasons:
        reasons_text = "\n".join(f"- {r}" for r in key_reasons[:3])
        lines.append(f"**核心理由:**\n{reasons_text}")

    risks = decision.get("risks", []) if isinstance(decision, dict) else []
    if risks:
        risks_text = "\n".join(f"- {r}" for r in risks[:3])
        lines.append(f"**风险:**\n{risks_text}")

    body = "\n\n".join(lines) if lines else "AI 决策已生成，请查看详细报告。"

    _send(subject, body)


def notify_trade_decision_failed(symbol: str, reason: str) -> None:
    """交易决策失败推送."""
    subject = f"⚠️ AI 决策失败 | {symbol}"
    body = f"**原因:** {reason[:300]}"

    _send(subject, body)


# ---------------------------------------------------------------------------
# Action Alerts
# ---------------------------------------------------------------------------

def notify_action_alerts(alerts: list[dict]) -> None:
    """行动建议推送."""
    if not alerts:
        return

    subject = f"🎯 行动建议 | {len(alerts)} 条"

    lines = []
    for alert in alerts[:5]:
        symbol = alert.get("symbol", "")
        title = alert.get("title", "")
        alert_type = alert.get("alert_type", "")
        lines.append(f"- **{symbol}** [{alert_type}] {title}")

    if len(alerts) > 5:
        lines.append(f"...及其他 {len(alerts) - 5} 条")

    body = "\n".join(lines)

    _send(subject, body)


# ---------------------------------------------------------------------------
# 系统异常
# ---------------------------------------------------------------------------

def notify_system_error(component: str, error: str) -> None:
    """系统异常推送."""
    subject = f"🚨 系统异常 | {component}"
    body = f"**错误:** {error[:500]}"

    _send(subject, body)
