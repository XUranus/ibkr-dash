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


# Track recently sent review dates to avoid duplicate pushes
_recently_sent_reviews: set[str] = set()


def notify_daily_review_completed(document: dict) -> None:
    """每日复盘完成推送 — 精简格式，只推摘要+归因+风险."""
    report_date = document.get("report_date", "")

    # Dedup: skip if already sent for this report_date
    if report_date in _recently_sent_reviews:
        logger.info("DailyReview notification skipped (already sent): date=%s", report_date)
        return

    # Skip if no meaningful content (no account data)
    summary = _pick(document, "summary")
    conclusion = _pick(document, "account_conclusion")
    contributors = _pick_list(document, "major_contributors_analysis")
    drags = _pick_list(document, "major_drags_analysis")

    # Detect empty/no-data reviews
    _no_data_markers = [
        "No account performance data",
        "Account data is unavailable",
        "Insufficient data",
        "数据不可用",
        "无法生成",
    ]
    combined = f"{summary} {conclusion}".strip()
    if any(marker.lower() in combined.lower() for marker in _no_data_markers) and not contributors:
        logger.info("DailyReview notification skipped (no data): date=%s", report_date)
        return

    fallback = document.get("fallback_used", False)
    tag = "📊" if not fallback else "📋"
    subject = f"{tag} 每日复盘 | {report_date}"

    lines = []

    # 1. 摘要（一行）
    if summary:
        lines.append(summary)

    # 2. 贡献者 / 拖累者（紧凑格式）
    if contributors:
        c_lines = []
        for item in contributors:
            sym = item.get("symbol", "")
            analysis = item.get("analysis", "")
            if sym:
                # Truncate analysis for push brevity
                short = analysis[:80] + "..." if len(analysis) > 80 else analysis
                c_lines.append(f"  ✅ {sym}: {short}")
        if c_lines:
            lines.append("贡献者:")
            lines.extend(c_lines)

    if drags:
        d_lines = []
        for item in drags:
            sym = item.get("symbol", "")
            analysis = item.get("analysis", "")
            if sym:
                short = analysis[:80] + "..." if len(analysis) > 80 else analysis
                d_lines.append(f"  ❌ {sym}: {short}")
        if d_lines:
            lines.append("拖累者:")
            lines.extend(d_lines)

    # 3. 风险提醒（如果有）
    risk = _pick(document, "risk_analysis")
    if risk and "没有明显" not in risk and len(risk) > 5:
        lines.append(f"⚠️ {risk}")

    # 4. 明日关注（只取前2个，一行一个）
    watchlist = _pick_list(document, "tomorrow_watchlist")
    if watchlist:
        watch_lines = []
        for item in watchlist[:2]:
            sym = item.get("symbol", "")
            reason = item.get("reason", "")
            if sym and reason:
                watch_lines.append(f"  👁 {sym}: {reason[:50]}")
        if watch_lines:
            lines.append("明日关注:")
            lines.extend(watch_lines)

    body = "\n".join(lines) if lines else "复盘报告已生成，请查看详情。"

    # Limit push body length
    if len(body) > 800:
        body = body[:797] + "..."

    logger.info("DailyReview notification: date=%s fallback=%s body_len=%d", report_date, fallback, len(body))
    _send(subject, body)
    _recently_sent_reviews.add(report_date)


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
