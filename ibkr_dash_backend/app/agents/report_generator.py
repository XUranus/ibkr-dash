"""Bilingual report generator for AI agent outputs.

Generates Chinese and English markdown reports from structured AI output,
stores them locally, and provides self-verification.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Reports directory relative to project root
_REPORTS_DIR = Path(__file__).resolve().parents[2] / "data" / "reports"


def _ensure_reports_dir() -> Path:
    """Ensure the reports directory exists."""
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return _REPORTS_DIR


def generate_trade_decision_report(
    decision: dict,
    symbol: str,
    lang: str = "zh",
) -> str:
    """Generate a markdown report for a trade decision.

    Args:
        decision: The trade decision output dict.
        symbol: Stock symbol.
        lang: Language code ('zh' or 'en').

    Returns:
        Markdown string.
    """
    if lang == "zh":
        return _build_decision_report_zh(decision, symbol)
    return _build_decision_report_en(decision, symbol)


def generate_trade_review_report(
    review: dict,
    symbol: str,
    lang: str = "zh",
) -> str:
    """Generate a markdown report for a trade review.

    Args:
        review: The trade review output dict.
        symbol: Stock symbol.
        lang: Language code ('zh' or 'en').

    Returns:
        Markdown string.
    """
    if lang == "zh":
        return _build_review_report_zh(review, symbol)
    return _build_review_report_en(review, symbol)


def save_report(
    report_type: str,
    symbol: str,
    content_zh: str,
    content_en: str,
    report_id: str | None = None,
) -> dict[str, str]:
    """Save bilingual reports to local files.

    Args:
        report_type: 'trade_decision' or 'trade_review'.
        symbol: Stock symbol.
        content_zh: Chinese markdown content.
        content_en: English markdown content.
        report_id: Optional ID for naming.

    Returns:
        Dict with file paths.
    """
    reports_dir = _ensure_reports_dir()
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    rid = report_id or date_str

    zh_path = reports_dir / f"{report_type}_{symbol}_{rid}_zh.md"
    en_path = reports_dir / f"{report_type}_{symbol}_{rid}_en.md"

    zh_path.write_text(content_zh, encoding="utf-8")
    en_path.write_text(content_en, encoding="utf-8")

    logger.info("Saved reports: %s, %s", zh_path.name, en_path.name)
    return {"zh": str(zh_path), "en": str(en_path)}


def verify_decision(decision: dict) -> dict[str, Any]:
    """Self-verify a trade decision for consistency.

    Checks:
    - Score vs rating consistency
    - Action vs confidence consistency
    - Required fields present
    - Data quality flags

    Returns:
        Dict with verification results.
    """
    issues: list[str] = []
    warnings: list[str] = []

    score = decision.get("overall_score", 0)
    rating = decision.get("rating", "")
    action = decision.get("action", "")
    confidence = decision.get("confidence", "")

    # Score vs rating
    if score >= 70 and rating not in ("positive", "strong_positive"):
        issues.append(f"Score {score} suggests positive but rating is '{rating}'")
    elif score <= 30 and rating not in ("negative", "strong_negative"):
        issues.append(f"Score {score} suggests negative but rating is '{rating}'")
    elif 30 < score < 70 and rating not in ("neutral",):
        warnings.append(f"Score {score} is neutral range but rating is '{rating}'")

    # Action vs confidence
    if action in ("add", "sell") and confidence == "low":
        warnings.append(f"Action '{action}' with low confidence is risky")

    # Required fields
    if not decision.get("decision_summary"):
        issues.append("Missing decision_summary")
    if not decision.get("key_reasons"):
        warnings.append("No key_reasons provided")

    # Data limitations
    data_limits = decision.get("data_limitations", [])
    if len(data_limits) > 3:
        warnings.append(f"Many data limitations ({len(data_limits)}); analysis may be unreliable")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "score": score,
        "rating": rating,
    }


def verify_review(review: dict) -> dict[str, Any]:
    """Self-verify a trade review for consistency.

    Returns:
        Dict with verification results.
    """
    issues: list[str] = []
    warnings: list[str] = []

    score = review.get("overall_score", 0)
    rating = review.get("rating", "")

    # Score vs rating
    if score >= 70 and rating not in ("positive", "strong_positive"):
        issues.append(f"Score {score} suggests positive but rating is '{rating}'")
    elif score <= 30 and rating not in ("negative", "strong_negative"):
        issues.append(f"Score {score} suggests negative but rating is '{rating}'")

    # Required fields
    if not review.get("summary"):
        issues.append("Missing summary")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Chinese report builders
# ---------------------------------------------------------------------------

def _build_decision_report_zh(decision: dict, symbol: str) -> str:
    """Build Chinese markdown report for trade decision."""
    score = decision.get("overall_score", 0)
    rating = decision.get("rating", "neutral")
    action = decision.get("action", "watchlist")
    confidence = decision.get("confidence", "low")
    summary = decision.get("decision_summary", "")
    reasons = decision.get("key_reasons", [])
    risks = decision.get("major_risks", [])
    limitations = decision.get("data_limitations", [])

    # Rating emoji
    rating_map = {
        "strong_positive": "🟢 强烈看好",
        "positive": "🟢 看好",
        "neutral": "🟡 中性",
        "negative": "🔴 看空",
        "strong_negative": "🔴 强烈看空",
    }
    rating_display = rating_map.get(rating, f"⚪ {rating}")

    # Action map
    action_map = {
        "add": "📈 加仓",
        "hold": "✋ 持有",
        "reduce": "📉 减仓",
        "sell": "🔴 卖出",
        "wait": "⏳ 等待",
        "avoid": "🚫 回避",
        "watchlist": "👀 观察",
    }
    action_display = action_map.get(action, action)

    # Confidence map
    conf_map = {
        "high": "高",
        "medium": "中",
        "low": "低",
    }
    conf_display = conf_map.get(confidence, confidence)

    lines = [
        f"# 📊 交易决策分析 — {symbol}",
        "",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
        "## 📋 决策摘要",
        "",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| 综合评分 | **{score:.0f}**/100 |",
        f"| 评级 | {rating_display} |",
        f"| 建议操作 | {action_display} |",
        f"| 信心度 | {conf_display} |",
        "",
        f"**结论**: {summary}",
        "",
    ]

    # Key reasons
    if reasons:
        lines.extend([
            "## ✅ 看多/看空理由",
            "",
        ])
        for i, r in enumerate(reasons, 1):
            lines.append(f"{i}. {r}")
        lines.append("")

    # Risks
    if risks:
        lines.extend([
            "## ⚠️ 主要风险",
            "",
        ])
        for i, r in enumerate(risks, 1):
            lines.append(f"{i}. {r}")
        lines.append("")

    # Data limitations
    if limitations:
        lines.extend([
            "## 📉 数据限制",
            "",
        ])
        for l in limitations:
            lines.append(f"- {l}")
        lines.append("")

    # Score breakdown
    score_detail = decision.get("score_detail", {})
    if score_detail:
        lines.extend([
            "## 📊 评分明细",
            "",
            "| 维度 | 分数 | 立场 |",
            "|------|------|------|",
        ])
        for dim, detail in score_detail.items():
            if isinstance(detail, dict):
                dim_score = detail.get("score", 0)
                stance = detail.get("stance", "-")
                lines.append(f"| {dim} | {dim_score} | {stance} |")
        lines.append("")

    # Position advice
    pos_adv = decision.get("position_advice", {})
    if pos_adv:
        lines.extend([
            "## 💼 仓位建议",
            "",
        ])
        for k, v in pos_adv.items():
            if v:
                lines.append(f"- **{k}**: {v}")
        lines.append("")

    lines.extend([
        "---",
        "",
        f"*本报告由 AI 交易决策系统自动生成，仅供参考，不构成投资建议。*",
    ])

    return "\n".join(lines)


def _build_review_report_zh(review: dict, symbol: str) -> str:
    """Build Chinese markdown report for trade review."""
    score = review.get("overall_score", 0)
    rating = review.get("rating", "neutral")
    summary = review.get("summary", "")
    strengths = review.get("strengths", [])
    weaknesses = review.get("weaknesses", [])
    mistakes = review.get("mistake_tags", [])
    suggestions = review.get("improvement_suggestions", [])
    limitations = review.get("data_limitations", [])

    rating_map = {
        "positive": "🟢 良好",
        "neutral": "🟡 一般",
        "negative": "🔴 较差",
    }
    rating_display = rating_map.get(rating, f"⚪ {rating}")

    lines = [
        f"# 📝 交易复盘 — {symbol}",
        "",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
        "## 📋 复盘摘要",
        "",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| 综合评分 | **{score:.0f}**/100 |",
        f"| 评级 | {rating_display} |",
        "",
        f"**总结**: {summary}",
        "",
    ]

    # Strengths
    if strengths:
        lines.extend([
            "## ✅ 优点",
            "",
        ])
        for s in strengths:
            lines.append(f"- {s}")
        lines.append("")

    # Weaknesses
    if weaknesses:
        lines.extend([
            "## ❌ 不足",
            "",
        ])
        for w in weaknesses:
            lines.append(f"- {w}")
        lines.append("")

    # Mistakes
    if mistakes:
        lines.extend([
            "## 🏷️ 错误标签",
            "",
        ])
        for m in mistakes:
            lines.append(f"- `{m}`")
        lines.append("")

    # Suggestions
    if suggestions:
        lines.extend([
            "## 💡 改进建议",
            "",
        ])
        for i, s in enumerate(suggestions, 1):
            lines.append(f"{i}. {s}")
        lines.append("")

    # Limitations
    if limitations:
        lines.extend([
            "## 📉 数据限制",
            "",
        ])
        for l in limitations:
            lines.append(f"- {l}")
        lines.append("")

    lines.extend([
        "---",
        "",
        f"*本报告由 AI 交易复盘系统自动生成，仅供参考。*",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# English report builders
# ---------------------------------------------------------------------------

def _build_decision_report_en(decision: dict, symbol: str) -> str:
    """Build English markdown report for trade decision."""
    score = decision.get("overall_score", 0)
    rating = decision.get("rating", "neutral")
    action = decision.get("action", "watchlist")
    confidence = decision.get("confidence", "low")
    summary = decision.get("decision_summary", "")
    reasons = decision.get("key_reasons", [])
    risks = decision.get("major_risks", [])
    limitations = decision.get("data_limitations", [])

    rating_map = {
        "strong_positive": "🟢 Strong Buy",
        "positive": "🟢 Buy",
        "neutral": "🟡 Neutral",
        "negative": "🔴 Sell",
        "strong_negative": "🔴 Strong Sell",
    }
    rating_display = rating_map.get(rating, f"⚪ {rating}")

    action_map = {
        "add": "📈 Add",
        "hold": "✋ Hold",
        "reduce": "📉 Reduce",
        "sell": "🔴 Sell",
        "wait": "⏳ Wait",
        "avoid": "🚫 Avoid",
        "watchlist": "👀 Watchlist",
    }
    action_display = action_map.get(action, action)

    conf_map = {"high": "High", "medium": "Medium", "low": "Low"}
    conf_display = conf_map.get(confidence, confidence)

    lines = [
        f"# 📊 Trade Decision Analysis — {symbol}",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
        "## 📋 Decision Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Overall Score | **{score:.0f}**/100 |",
        f"| Rating | {rating_display} |",
        f"| Action | {action_display} |",
        f"| Confidence | {conf_display} |",
        "",
        f"**Conclusion**: {summary}",
        "",
    ]

    if reasons:
        lines.extend(["## ✅ Key Reasons", ""])
        for i, r in enumerate(reasons, 1):
            lines.append(f"{i}. {r}")
        lines.append("")

    if risks:
        lines.extend(["## ⚠️ Major Risks", ""])
        for i, r in enumerate(risks, 1):
            lines.append(f"{i}. {r}")
        lines.append("")

    if limitations:
        lines.extend(["## 📉 Data Limitations", ""])
        for l in limitations:
            lines.append(f"- {l}")
        lines.append("")

    score_detail = decision.get("score_detail", {})
    if score_detail:
        lines.extend(["## 📊 Score Breakdown", "", "| Dimension | Score | Stance |", "|-----------|-------|--------|"])
        for dim, detail in score_detail.items():
            if isinstance(detail, dict):
                lines.append(f"| {dim} | {detail.get('score', 0)} | {detail.get('stance', '-')} |")
        lines.append("")

    lines.extend([
        "---",
        "",
        "*This report is auto-generated by the AI trade decision system for reference only.*",
    ])

    return "\n".join(lines)


def _build_review_report_en(review: dict, symbol: str) -> str:
    """Build English markdown report for trade review."""
    score = review.get("overall_score", 0)
    rating = review.get("rating", "neutral")
    summary = review.get("summary", "")
    strengths = review.get("strengths", [])
    weaknesses = review.get("weaknesses", [])
    mistakes = review.get("mistake_tags", [])
    suggestions = review.get("improvement_suggestions", [])
    limitations = review.get("data_limitations", [])

    rating_map = {
        "positive": "🟢 Good",
        "neutral": "🟡 Average",
        "negative": "🔴 Poor",
    }
    rating_display = rating_map.get(rating, f"⚪ {rating}")

    lines = [
        f"# 📝 Trade Review — {symbol}",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
        "## 📋 Review Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Overall Score | **{score:.0f}**/100 |",
        f"| Rating | {rating_display} |",
        "",
        f"**Summary**: {summary}",
        "",
    ]

    if strengths:
        lines.extend(["## ✅ Strengths", ""])
        for s in strengths:
            lines.append(f"- {s}")
        lines.append("")

    if weaknesses:
        lines.extend(["## ❌ Weaknesses", ""])
        for w in weaknesses:
            lines.append(f"- {w}")
        lines.append("")

    if mistakes:
        lines.extend(["## 🏷️ Mistake Tags", ""])
        for m in mistakes:
            lines.append(f"- `{m}`")
        lines.append("")

    if suggestions:
        lines.extend(["## 💡 Improvement Suggestions", ""])
        for i, s in enumerate(suggestions, 1):
            lines.append(f"{i}. {s}")
        lines.append("")

    if limitations:
        lines.extend(["## 📉 Data Limitations", ""])
        for l in limitations:
            lines.append(f"- {l}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "*This report is auto-generated by the AI trade review system for reference only.*",
    ])

    return "\n".join(lines)
