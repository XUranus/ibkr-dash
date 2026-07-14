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

def notify_daily_review_completed(document: dict) -> None:
    """每日复盘完成推送."""
    report_date = document.get("report_date", "")
    summary = document.get("summary", "")
    conclusion = document.get("account_conclusion", "")
    status = document.get("status", "")

    subject = f"📊 每日复盘完成 | {report_date}"

    lines = []
    if conclusion:
        lines.append(f"**账户结论:** {conclusion[:200]}")
    if summary:
        lines.append(f"**摘要:** {summary[:300]}")
    lines.append(f"**状态:** {status}")
    body = "\n\n".join(lines)

    _send(subject, body)


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
