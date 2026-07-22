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
    """每日复盘完成推送 — 使用统一的 Markdown 内容（与 web admin 相同）."""
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

    # Use unified markdown content (same as web admin)
    body = document.get("review_markdown", "")
    if not body:
        # Fallback: generate markdown from document
        from app.agents.daily_review.agent import _generate_review_markdown
        body = _generate_review_markdown(document)

    # Markdown 允许更长内容
    if len(body) > 2000:
        body = body[:1997] + "..."

    logger.info("DailyReview notification: date=%s fallback=%s body_len=%d", report_date, fallback, len(body))
    _send(subject, body, fmt="markdown")
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
# 持仓分析
# ---------------------------------------------------------------------------

def notify_position_analysis_completed(document: dict) -> None:
    """持仓分析完成推送 — Markdown 格式，包含评分、建议、风险."""
    report_date = document.get("report_date", "")
    overall_score = document.get("overall_score", 0)
    rating = document.get("rating", "")
    summary = document.get("summary", "")

    rating_labels = {"excellent": "优秀", "good": "良好", "fair": "一般", "poor": "较差"}
    rating_label = rating_labels.get(rating, rating)

    subject = f"📊 持仓分析 | {report_date} | {overall_score}分 {rating_label}"

    lines: list[str] = []

    # 1. Summary
    if summary:
        lines.append(f"**{summary}**")
        lines.append("")

    # 2. Score breakdown
    score_detail = document.get("score_detail", {})
    if score_detail:
        lines.append("**📊 评分明细**")
        dim_labels = {
            "company_quality": "公司质量",
            "valuation_quality": "估值质量",
            "trend_strength": "趋势强度",
            "account_fit": "账户适配",
            "risk_reward": "风险收益",
            "review_constraints": "复盘约束",
            "event_catalyst": "事件催化",
        }
        for dim, info in score_detail.items():
            if isinstance(info, dict):
                score = info.get("score", 0)
                max_s = info.get("max_score", 0)
                reason = info.get("reason", "")
                label = dim_labels.get(dim, dim)
                lines.append(f"- {label}: {score}/{max_s} — {reason[:80]}")
        lines.append("")

    # 3. Position advice
    advice = document.get("position_advice", {})
    if isinstance(advice, dict) and advice.get("action"):
        action_labels = {"add": "加仓", "hold": "持有", "reduce": "减仓", "close": "清仓"}
        action_label = action_labels.get(advice["action"], advice["action"])
        lines.append(f"**💡 仓位建议:** {action_label}")
        if advice.get("rationale"):
            lines.append(f"  理由: {advice['rationale'][:100]}")
        lines.append("")

    # 4. Strengths
    strengths = document.get("strengths", [])
    if strengths:
        lines.append("**✅ 优点**")
        for s in strengths[:3]:
            lines.append(f"- {s[:80]}")
        lines.append("")

    # 5. Weaknesses
    weaknesses = document.get("weaknesses", [])
    if weaknesses:
        lines.append("**⚠️ 风险点**")
        for w in weaknesses[:3]:
            lines.append(f"- {w[:80]}")
        lines.append("")

    # 6. Key risks
    risks = document.get("key_risks", [])
    if risks:
        lines.append("**🔴 关键风险**")
        for r in risks[:3]:
            lines.append(f"- {r[:80]}")

    body = "\n".join(lines).strip() if lines else "持仓分析已生成，请查看详情。"
    if len(body) > 2000:
        body = body[:1997] + "..."

    _send(subject, body, fmt="markdown")


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

_ALERT_TYPE_LABELS: dict[str, str] = {
    "add_position_review": "加仓复核",
    "entry_position_review": "建仓复核",
    "reduce_position_review": "减仓复核",
    "risk_review": "风险复核",
}


def notify_action_alerts(alerts: list[dict]) -> None:
    """行动建议推送 — Markdown 格式，包含标题、原因、操作建议."""
    if not alerts:
        return

    subject = f"🎯 行动建议 | {len(alerts)} 条"

    lines: list[str] = []
    for alert in alerts[:5]:
        symbol = alert.get("display_symbol") or alert.get("symbol", "")
        title = alert.get("title", "")
        alert_type = alert.get("alert_type", "")
        reasons = alert.get("reason_summary", []) or []
        suggested = alert.get("suggested_user_action", "")
        confidence = alert.get("confidence", "")
        urgency = alert.get("urgency", "")

        # Human-readable type label instead of raw alert_type
        type_label = _ALERT_TYPE_LABELS.get(alert_type, alert_type)

        # Urgency icon
        urgency_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(urgency, "⚪")

        lines.append(f"**{urgency_icon} {symbol}** — {type_label}")
        if title:
            lines.append(f"  {title}")

        # Show top reasons (skip internal jargon)
        if reasons:
            human_reasons = []
            for r in reasons[:3]:
                # Skip overly technical reasons
                if any(skip in r for skip in ["未发现 high_risk", "未发现阻止", "dedupe_checked"]):
                    continue
                human_reasons.append(r)
            if human_reasons:
                lines.append(f"  原因: {'；'.join(human_reasons[:2])}")

        if suggested:
            lines.append(f"  👉 {suggested}")

        if confidence:
            conf_label = {"high": "高确信", "medium": "中确信", "low": "低确信"}.get(confidence, confidence)
            lines.append(f"  确信度: {conf_label}")

        lines.append("")

    if len(alerts) > 5:
        lines.append(f"*...及其他 {len(alerts) - 5} 条*")

    body = "\n".join(lines).strip()

    _send(subject, body, fmt="markdown")


# ---------------------------------------------------------------------------
# 系统异常
# ---------------------------------------------------------------------------

def notify_system_error(component: str, error: str) -> None:
    """系统异常推送."""
    subject = f"🚨 系统异常 | {component}"
    body = f"**错误:** {error[:500]}"

    _send(subject, body)
