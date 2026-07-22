from __future__ import annotations

from app.domains.portfolio_manager.action_alerts.schemas import PortfolioActionAlertCreate
from app.domains.portfolio_manager.common import ADD_LIKE_ACTIONS, ENTRY_BLOCKED_AI_ROLES, REDUCE_LIKE_ACTIONS, dedupe
from app.domains.portfolio_manager.daily_loop.schemas import PortfolioDailyLoopRun
from app.domains.portfolio_manager.decision_orchestrator.schemas import PortfolioAutoDecisionItem, PortfolioAutoDecisionRunDetail
from app.domains.portfolio_manager.portfolio_review.schemas import PortfolioManagerReport
from app.domains.portfolio_manager.watchtower.schemas import PortfolioWatchtowerRunDetail

RISK_WORDS = ("concentration", "risk", "overweight", "集中", "风险", "超配")


class PortfolioActionAlertBuilder:
    def build(
        self,
        *,
        daily_loop_run: PortfolioDailyLoopRun,
        auto_decision_run: PortfolioAutoDecisionRunDetail | None,
        portfolio_report: PortfolioManagerReport | None,
        watchtower_run: PortfolioWatchtowerRunDetail | None = None,
    ) -> list[PortfolioActionAlertCreate]:
        if auto_decision_run is None or portfolio_report is None:
            return []
        if daily_loop_run.options.dry_run_auto_decision:
            return []

        alerts: list[PortfolioActionAlertCreate] = []
        watchtower_by_item_id = {item.id: item for item in (watchtower_run.items if watchtower_run else [])}
        for item in auto_decision_run.items:
            if item.selection_status != "completed":
                continue
            action = _decision_action(item.decision_summary)
            if item.universe_type == "holding" and item.decision_type == "holding_decision" and action in ADD_LIKE_ACTIONS:
                if _blocks_add_or_entry(portfolio_report, item.symbol):
                    continue
                alerts.append(self._decision_alert(daily_loop_run, item, portfolio_report, "add_position_review", "consider_add", f"{item.display_symbol} 进入加仓复核区", watchtower_by_item_id.get(item.source_watchtower_item_id)))
            if item.universe_type in {"watchlist", "candidate"} and item.decision_type == "entry_decision" and action in ADD_LIKE_ACTIONS:
                if item.ai_theme_role in ENTRY_BLOCKED_AI_ROLES or _blocks_add_or_entry(portfolio_report, item.symbol):
                    continue
                alerts.append(self._decision_alert(daily_loop_run, item, portfolio_report, "entry_position_review", "consider_entry", f"{item.display_symbol} 出现建仓复核机会", watchtower_by_item_id.get(item.source_watchtower_item_id)))
            if item.universe_type == "holding" and action in REDUCE_LIKE_ACTIONS:
                alerts.append(self._decision_alert(daily_loop_run, item, portfolio_report, "reduce_position_review", "consider_reduce", f"{item.display_symbol} 进入减仓复核区", watchtower_by_item_id.get(item.source_watchtower_item_id)))
            if _item_has_high_risk(item):
                alerts.append(self._risk_alert(daily_loop_run, item, portfolio_report, ["Trade Decision 风险等级为 high"]))

        existing_risk_symbols = {alert.symbol for alert in alerts if alert.alert_type == "risk_review"}
        for symbol, reasons in _portfolio_risk_symbols(portfolio_report).items():
            if symbol in existing_risk_symbols:
                continue
            item = _find_item(auto_decision_run.items, symbol)
            if item and item.selection_status == "completed":
                alerts.append(self._risk_alert(daily_loop_run, item, portfolio_report, reasons))

        return _dedupe_alerts(alerts)

    def _decision_alert(
        self,
        daily_loop_run: PortfolioDailyLoopRun,
        item: PortfolioAutoDecisionItem,
        report: PortfolioManagerReport,
        alert_type: str,
        action_direction: str,
        title: str,
        watchtower_item,
    ) -> PortfolioActionAlertCreate:
        reasons = _base_reasons(item, report, watchtower_item)
        if alert_type == "reduce_position_review":
            reasons.append("这是减仓复核，不是卖出指令")
        return PortfolioActionAlertCreate(
            run_date=daily_loop_run.run_date,
            alert_type=alert_type,
            symbol=item.symbol,
            display_symbol=item.display_symbol,
            title=title,
            action_direction=action_direction,
            urgency=_urgency(item, report),
            confidence=_confidence(item),
            reason_summary=reasons,
            decision_summary=_decision_summary(item.decision_summary),
            portfolio_context=_portfolio_context(report),
            linked_ids=_linked_ids(daily_loop_run, item, report),
            suggested_user_action=_suggested_action(alert_type),
        )

    def _risk_alert(self, daily_loop_run: PortfolioDailyLoopRun, item: PortfolioAutoDecisionItem, report: PortfolioManagerReport, reasons: list[str]) -> PortfolioActionAlertCreate:
        # Build a descriptive title with specific risk context
        risk_parts: list[str] = []
        risk_level = str(item.decision_summary.get("risk_level") or "").lower()
        if risk_level:
            risk_parts.append(f"风险等级: {risk_level}")
        # Add concentration risk context
        if report.concentration_risk.assessment == "high" and item.symbol in report.concentration_risk.single_name_risk_symbols:
            risk_parts.append("集中度风险偏高")
        # Add portfolio health context
        if report.portfolio_health_level in {"attention_required", "high_risk"}:
            risk_parts.append(f"组合健康: {report.portfolio_health_level}")
        detail = "，".join(risk_parts) if risk_parts else "需要人工复核"
        title = f"{item.display_symbol} 风险预警 — {detail}"

        # Enrich reasons with specific portfolio metrics
        enriched_reasons = list(reasons)
        if report.concentration_risk.assessment == "high":
            enriched_reasons.append(f"组合集中度评估为 high")
        if report.portfolio_health_level in {"attention_required", "high_risk"}:
            enriched_reasons.append(f"组合健康状态: {report.portfolio_health_level}")

        return PortfolioActionAlertCreate(
            run_date=daily_loop_run.run_date,
            alert_type="risk_review",
            symbol=item.symbol,
            display_symbol=item.display_symbol,
            title=title,
            action_direction="review_risk",
            urgency="high",
            confidence=_confidence(item),
            reason_summary=dedupe([*enriched_reasons, *_base_reasons(item, report, None)]),
            decision_summary=_decision_summary(item.decision_summary),
            portfolio_context=_portfolio_context(report),
            linked_ids=_linked_ids(daily_loop_run, item, report),
            suggested_user_action="查看该仓位的决策详情和组合报告，评估是否需要调整仓位或止损。",
        )


def _decision_action(decision_summary: dict) -> str:
    for key in ("risk_adjusted_action", "final_action"):
        value = str(decision_summary.get(key) or "").strip().lower()
        if value:
            return value
    return ""


def _decision_summary(value: dict) -> dict:
    keys = ("final_action", "risk_adjusted_action", "target_position_pct", "max_position_pct", "confidence", "risk_level")
    return {key: value.get(key) for key in keys if key in value}


def _portfolio_context(report: PortfolioManagerReport) -> dict:
    return {
        "portfolio_health_score": report.portfolio_health_score,
        "portfolio_health_level": report.portfolio_health_level,
        "cash_status": report.cash_status.assessment,
        "concentration_risk": report.concentration_risk.assessment,
        "ai_theme_exposure_assessment": report.ai_theme_exposure.assessment,
    }


def _linked_ids(daily_loop_run: PortfolioDailyLoopRun, item: PortfolioAutoDecisionItem, report: PortfolioManagerReport) -> dict:
    return {
        "daily_loop_run_id": daily_loop_run.id,
        "watchtower_run_id": daily_loop_run.linked_run_ids.get("watchtower_run_id") or item.source_watchtower_run_id,
        "auto_decision_run_id": item.run_id,
        "auto_decision_item_id": item.id,
        "decision_id": item.decision_id,
        "portfolio_report_id": report.id,
    }


_ACTION_LABELS: dict[str, str] = {
    "add": "加仓", "add_small": "小幅加仓", "add_batch": "分批加仓",
    "add_on_pullback": "回调加仓", "add_right_side": "右侧加仓",
    "buy": "买入", "build_position": "建仓", "accumulate": "累积",
    "increase": "增持", "reduce": "减仓", "reduce_batch": "分批减仓",
    "reduce_now": "立即减仓", "trim_on_rebound": "反弹减仓",
    "sell": "卖出", "sell_thesis_broken": "逻辑破坏卖出", "trim": "止盈",
    "hold": "持有", "hold_position": "持仓观望",
}


def _base_reasons(item: PortfolioAutoDecisionItem, report: PortfolioManagerReport, watchtower_item) -> list[str]:
    reasons = []
    if item.watchtower_status == "decision_required":
        reasons.append("监控系统发现该仓位需要关注")
    if watchtower_item:
        reasons.extend([f"监控信号: {reason.message}" for reason in watchtower_item.trigger_reasons[:3]])
    action = _decision_action(item.decision_summary)
    if action:
        action_label = _ACTION_LABELS.get(action, action)
        reasons.append(f"AI 决策建议: {action_label}")
    return dedupe(reasons)


def _blocks_add_or_entry(report: PortfolioManagerReport, symbol: str) -> bool:
    if report.portfolio_health_level == "high_risk":
        return True
    return report.concentration_risk.assessment == "high" and symbol in report.concentration_risk.single_name_risk_symbols


def _item_has_high_risk(item: PortfolioAutoDecisionItem) -> bool:
    return str(item.decision_summary.get("risk_level") or "").lower() == "high"


def _portfolio_risk_symbols(report: PortfolioManagerReport) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for item in report.action_queue:
        reason = item.reason or ""
        if item.queue_type == "manual_review" and any(word in reason.lower() for word in RISK_WORDS):
            result.setdefault(item.symbol, []).append(f"组合报告标记需要人工复核：{reason}")
    for gap in report.allocation_gaps:
        if gap.gap_type == "overweight" and gap.priority == "high":
            result.setdefault(gap.symbol, []).append(f"仓位超配: {gap.gap_reason}")
    if report.concentration_risk.assessment == "high":
        for symbol in report.concentration_risk.single_name_risk_symbols:
            result.setdefault(symbol, []).append("该标的集中度风险偏高")
    return result


def _find_item(items: list[PortfolioAutoDecisionItem], symbol: str) -> PortfolioAutoDecisionItem | None:
    return next((item for item in items if item.symbol == symbol), None)


def _urgency(item: PortfolioAutoDecisionItem, report: PortfolioManagerReport) -> str:
    if item.watchtower_severity == "high" or report.portfolio_health_level in {"attention_required", "high_risk"}:
        return "high"
    if item.watchtower_severity == "medium" or report.portfolio_health_level == "watch":
        return "medium"
    return "low"


def _confidence(item: PortfolioAutoDecisionItem) -> str:
    value = str(item.decision_summary.get("confidence") or "").lower()
    return value if value in {"low", "medium", "high"} else "medium"


def _suggested_action(alert_type: str) -> str:
    return {
        "add_position_review": "打开交易决策详情，人工确认是否加仓。",
        "entry_position_review": "打开交易决策详情，人工确认是否建仓。",
        "reduce_position_review": "打开交易决策详情，人工确认是否减仓或止盈；这不是卖出指令。",
        "risk_review": "打开组合报告和交易决策详情，人工复核仓位风险。",
    }.get(alert_type, "请人工复核相关交易决策详情。")


def _dedupe_alerts(alerts: list[PortfolioActionAlertCreate]) -> list[PortfolioActionAlertCreate]:
    result: list[PortfolioActionAlertCreate] = []
    seen: set[tuple[str, str]] = set()
    for alert in alerts:
        key = (alert.symbol, alert.alert_type)
        if key in seen:
            continue
        seen.add(key)
        result.append(alert)
    return result
