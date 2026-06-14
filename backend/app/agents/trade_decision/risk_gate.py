"""
Trade Decision Risk Gate — deterministic gating layer that runs after the
composer and before the final action is published.

Goals:
1. Make actions safe by enforcing hard risk constraints:
   - No "add" actions without a position limit.
   - No "add" actions without invalidation conditions.
   - No "add" / "add_batch" when catalyst is weak.
   - No "add" when current position already meets/exceeds max position.
   - Detect and block panic-driven "sell" asks when thesis is intact.
2. Expand the action vocabulary with explicit semantics:
   - hold_no_add, add_on_pullback, add_right_side, trim_on_rebound,
     reduce_now, sell_thesis_broken, panic_blocked.
3. Surface `risk_gate` block in decision_output so downstream consumers
   (frontend / eval) can see the reasons for any downgrade.

The gate is intentionally deterministic and does NOT call LLM/MCP.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.trade_decision.cards import (
    AccountFactSnapshot,
    AccountFitCard,
    CardStance,
    EventCatalystCard,
    FundamentalValuationCard,
    MarketTrendCard,
    RiskRewardCard,
    TradeDecisionCardPack,
)


# Action vocabulary
RISK_GATE_ACTIONS = {
    "add", "add_small", "add_batch", "hold", "reduce", "reduce_batch",
    "sell", "wait", "avoid", "watchlist",
    "hold_no_add", "add_on_pullback", "add_right_side",
    "trim_on_rebound", "reduce_now", "sell_thesis_broken", "panic_blocked",
}

ADD_LIKE_ACTIONS = {"add", "add_small", "add_batch", "add_on_pullback", "add_right_side"}
STRONG_ADD_ACTIONS = {"add", "add_batch", "add_right_side"}
HOLD_LIKE_ACTIONS = {"hold", "hold_no_add", "wait", "watchlist", "avoid"}
EXIT_LIKE_ACTIONS = {"sell", "sell_thesis_broken", "reduce", "reduce_batch", "trim_on_rebound", "reduce_now"}

PANIC_TOKENS_ZH = (
    "清仓", "割肉", "受不了", "暴跌", "恐慌", "大跌", "赶紧卖", "全卖", "都卖", "卖掉", "快卖", "我要卖", "全部卖出",
)
PANIC_TOKENS_EN = (
    "panic sell", "sell everything", "dump it", "cut loss", "cut my losses",
    "i can't take it", "market crash", "blood bath", "bloodbath",
)


@dataclass
class RiskGateResult:
    original_action: str
    final_action: str
    blocked: bool
    downgraded: bool
    gate_reasons: list[str]
    required_disclosures: list[str]
    risk_flags: list[str]
    action_constraints: dict
    confidence_cap: str | None = None
    failed: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_action": self.original_action,
            "final_action": self.final_action,
            "blocked": self.blocked,
            "downgraded": self.downgraded,
            "gate_reasons": list(self.gate_reasons),
            "required_disclosures": list(self.required_disclosures),
            "risk_flags": list(self.risk_flags),
            "action_constraints": dict(self.action_constraints),
            "confidence_cap": self.confidence_cap,
            "failed": self.failed,
            "error": self.error,
        }


CONFIDENCE_ORDER = ["low", "medium", "high"]


def _clamp_confidence(current: str | None, cap: str | None) -> str:
    if not cap:
        return current or "low"
    cur_idx = CONFIDENCE_ORDER.index(current) if current in CONFIDENCE_ORDER else 0
    cap_idx = CONFIDENCE_ORDER.index(cap) if cap in CONFIDENCE_ORDER else 0
    return CONFIDENCE_ORDER[min(cur_idx, cap_idx)]


@dataclass
class _GateContext:
    """Mutable state passed through gate rule groups."""
    action: str
    reasons: list[str]
    flags: list[str]
    disclosures: list[str]
    constraints: dict[str, Any]


class RiskGate:
    """Deterministic risk gate applied to a composed trade decision."""

    def evaluate(
        self,
        decision_output: dict[str, Any],
        card_pack: TradeDecisionCardPack,
        user_question: str | None = None,
    ) -> RiskGateResult:
        original_action = str(decision_output.get("action") or "watchlist")
        ctx = _GateContext(
            action=original_action, reasons=[], flags=[],
            disclosures=[], constraints={},
        )

        acc = card_pack.account_fit_card
        mkt = card_pack.market_trend_card
        fund = card_pack.fundamental_valuation_card
        evt = card_pack.event_catalyst_card
        rr = card_pack.risk_reward_card

        position_advice = decision_output.get("position_advice") or {}
        max_pct = _safe_float(position_advice.get("max_position_pct"))
        current_pct = _safe_float(position_advice.get("current_position_pct"))
        suggested_target_pct = _safe_float(position_advice.get("suggested_target_position_pct"))
        invalid_conditions = list((decision_output.get("execution_plan") or {}).get("invalid_conditions") or [])
        public_fallback_count = _count_public_fallback(card_pack)
        trend_break_level = _get_trend_break_level(mkt)
        holding = _is_holding(card_pack)

        # -- 0. Panic detection (short-circuits all other rules)
        panic = self._detect_panic(user_question, decision_output, card_pack)
        if panic:
            return self._panic_result(original_action, panic)

        # -- 1-5. Position & data quality gates
        self._check_position_limits(ctx, card_pack, max_pct, current_pct, invalid_conditions, holding)
        self._check_data_quality(ctx, card_pack, rr, mkt, fund, evt, public_fallback_count, holding)

        # -- 6. Technical trend-break gates
        self._check_trend_break(ctx, trend_break_level, holding)

        # -- 6b. Investment thesis gates
        self._check_investment_thesis(ctx, card_pack, current_pct, trend_break_level, fund, holding)

        # -- 6c. Fundamental status gates
        self._check_fundamental(ctx, fund, holding)

        # -- 6d. Risk/reward R-multiple gates
        self._check_rr_ratio(ctx, rr, holding)

        # -- 7-8. Severe breakdown & target validation
        self._check_severe_breakdown(ctx, mkt, evt, fund, holding)
        if max_pct is not None and suggested_target_pct is not None and max_pct > 0 and suggested_target_pct > max_pct + 1e-6:
            ctx.flags.append("target_above_max_position")

        return RiskGateResult(
            original_action=original_action,
            final_action=ctx.action,
            blocked=original_action != ctx.action and ctx.action in {"panic_blocked", "sell_thesis_broken"},
            downgraded=original_action != ctx.action,
            gate_reasons=ctx.reasons,
            required_disclosures=ctx.disclosures,
            risk_flags=ctx.flags,
            action_constraints={
                **ctx.constraints,
                "snapshot": {
                    "current_position_pct": current_pct,
                    "max_position_pct": max_pct,
                    "public_fallback_count": public_fallback_count,
                    "catalyst_strength": getattr(evt, "catalyst_strength", None) if evt else None,
                    "trend_break_level": trend_break_level,
                },
            },
            confidence_cap=_compute_confidence_cap(public_fallback_count=public_fallback_count, mkt=mkt, fund=fund, rr=rr, flags=ctx.flags),
        )

    # -- Rule group: position limits & invalidation --
    def _check_position_limits(self, ctx: _GateContext, card_pack, max_pct, current_pct, invalid_conditions, holding):
        if ctx.action in ADD_LIKE_ACTIONS and (max_pct is None or max_pct <= 0):
            ctx.action = "hold_no_add" if holding else "wait"
            ctx.reasons.append("缺少最大仓位上限，不能输出加仓建议")
            ctx.flags.append("missing_position_limit")
            ctx.constraints["required"] = ["max_position_pct"]
        if ctx.action in STRONG_ADD_ACTIONS and not invalid_conditions:
            ctx.action = "add_on_pullback" if not holding else "hold_no_add"
            ctx.reasons.append("缺少失效条件，强加仓已降级")
            ctx.flags.append("missing_invalidation_conditions")
        if ctx.action in ADD_LIKE_ACTIONS:
            acc = card_pack.account_fit_card
            at_limit = max_pct is not None and current_pct is not None and max_pct > 0 and current_pct >= max_pct
            poor_fit = bool(acc and acc.account_fit_level in ("concentrated", "poor"))
            if at_limit or poor_fit:
                ctx.action = "hold_no_add"
                ctx.reasons.append("已达仓位上限或账户适配度低，禁止继续加仓")
                ctx.flags.append("position_limit_reached")

    # -- Rule group: data quality & catalyst --
    def _check_data_quality(self, ctx: _GateContext, card_pack, rr, mkt, fund, evt, public_fallback_count, holding):
        insufficient = public_fallback_count >= 2 or _low_quality_evidence(rr) or _low_quality_evidence(mkt) or _low_quality_evidence(fund)
        if insufficient and ctx.action in ADD_LIKE_ACTIONS:
            ctx.action = "hold_no_add" if holding else "wait"
            ctx.reasons.append("公开市场数据不足/质量偏低，禁止输出加仓")
            ctx.flags.append("insufficient_data")
        if ctx.action in ADD_LIKE_ACTIONS and _is_weak_catalyst(evt):
            ctx.action = "wait" if not holding else "hold_no_add"
            ctx.reasons.append("催化偏弱，加仓已降级")
            ctx.flags.append("weak_catalyst_downgrade")

    # -- Rule group: technical trend-break --
    def _check_trend_break(self, ctx: _GateContext, trend_break_level: str, holding: bool):
        if trend_break_level == "severe" and ctx.action in ADD_LIKE_ACTIONS:
            ctx.action = "hold_no_add" if holding else "wait"
            ctx.reasons.append("技术面 severe trend break，禁止加仓")
            ctx.flags.append("trend_break_severe_blocked")
        if trend_break_level == "broken" and ctx.action in ADD_LIKE_ACTIONS:
            ctx.action = "hold_no_add" if holding else "wait"
            ctx.reasons.append("技术面 broken trend，禁止加仓")
            ctx.flags.append("trend_break_broken_blocked")
        if trend_break_level == "warning" and ctx.action in {"add", "add_batch", "add_right_side"}:
            ctx.action = "add_on_pullback" if not holding else "hold_no_add"
            ctx.reasons.append("技术面 trend break warning，禁止追涨加仓")
            ctx.flags.append("trend_break_warning_downgrade")

    # -- Rule group: investment thesis --
    def _check_investment_thesis(self, ctx: _GateContext, card_pack, current_pct, trend_break_level, fund, holding):
        thesis = card_pack.investment_thesis or {}
        thesis_max = _safe_float(thesis.get("max_position_pct")) if isinstance(thesis, dict) else None
        thesis_risk = str(thesis.get("risk_class") or "unknown") if isinstance(thesis, dict) else "unknown"

        if ctx.action in ADD_LIKE_ACTIONS and thesis_max and current_pct is not None and thesis_max > 0 and current_pct >= thesis_max:
            ctx.action = "hold_no_add"
            ctx.reasons.append("已达到投资假设最大仓位，禁止继续加仓")
            ctx.flags.append("thesis_position_limit")
        if thesis_risk == "extreme" and ctx.action in {"add", "add_batch", "add_right_side"}:
            ctx.action = "add_on_pullback" if not holding else "hold_no_add"
            ctx.reasons.append("高波动/极端标的，禁止强加仓")
            ctx.flags.append("thesis_extreme_risk_blocked")

        # sell_triggers
        try:
            from app.services.investment_thesis import evaluate_sell_triggers
            sell_triggers_hit = evaluate_sell_triggers(
                _thesis_from_dict(thesis), trend_break_level=trend_break_level,
                fundamental_red=_is_fundamental_red(fund),
            )
        except Exception:
            sell_triggers_hit = []
        if sell_triggers_hit and ctx.action in {"hold", "watchlist", "wait", "add_on_pullback", "hold_no_add"} and holding:
            ctx.action = "sell_thesis_broken" if thesis_risk in {"extreme", "high_growth"} else "reduce_now"
            ctx.reasons.append(f"投资假设 sell_triggers 命中: {'; '.join(sell_triggers_hit[:2])}")
            ctx.flags.append("thesis_sell_trigger_hit")

        # no_add_triggers
        try:
            from app.services.investment_thesis import evaluate_no_add_triggers
            no_add_hit = evaluate_no_add_triggers(
                _thesis_from_dict(thesis), position_pct=current_pct,
                trend_break_level=trend_break_level,
            )
        except Exception:
            no_add_hit = []
        if no_add_hit and ctx.action in ADD_LIKE_ACTIONS:
            ctx.action = "hold_no_add" if holding else "wait"
            ctx.reasons.append(f"投资假设 no_add_triggers 命中: {'; '.join(no_add_hit[:2])}")
            ctx.flags.append("thesis_no_add_trigger_hit")

    # -- Rule group: fundamental status --
    def _check_fundamental(self, ctx: _GateContext, fund, holding: bool):
        fundamental_status = _get_fundamental_status(fund)
        thesis_broken = bool(getattr(fund, "thesis_broken", False)) if fund else False
        if (fundamental_status == "red" or thesis_broken) and holding:
            target = "sell_thesis_broken" if thesis_broken else "reduce_now"
            if ctx.action in {"hold", "watchlist", "wait", "add_on_pullback", "hold_no_add", "add", "add_batch", "add_right_side", "add_small"}:
                ctx.action = target
            ctx.reasons.append("基本面 red 或投资假设被破坏，已转为减仓/退出")
            ctx.flags.append("fundamental_red_action")
        elif (fundamental_status == "red" or thesis_broken) and not holding:
            if ctx.action in ADD_LIKE_ACTIONS:
                ctx.action = "wait"
                ctx.reasons.append("基本面 red，禁止建仓")
                ctx.flags.append("fundamental_red_blocked")
        if fundamental_status == "orange" and ctx.action in ADD_LIKE_ACTIONS:
            ctx.action = "hold_no_add" if holding else "wait"
            ctx.reasons.append("基本面 orange，禁止加仓")
            ctx.flags.append("fundamental_orange_blocked")
        if fundamental_status == "yellow" and ctx.action in {"add", "add_batch", "add_right_side"}:
            ctx.action = "add_on_pullback" if not holding else "hold_no_add"
            ctx.reasons.append("基本面 yellow，禁止强加仓")
            ctx.flags.append("fundamental_yellow_downgrade")

    # -- Rule group: risk/reward R-multiple --
    def _check_rr_ratio(self, ctx: _GateContext, rr, holding: bool):
        rr_ratio = _safe_float(getattr(rr, "reward_risk_ratio", None)) if rr else None
        rr_downside = _safe_float(getattr(rr, "downside_risk_pct", None)) if rr else None
        if rr_ratio is not None and rr_ratio < 1.0 and ctx.action in ADD_LIKE_ACTIONS:
            ctx.action = "reduce_now" if holding else "wait"
            ctx.reasons.append(f"风险收益比 {rr_ratio:.2f} < 1.0，禁止加仓")
            ctx.flags.append("rr_below_one")
        elif rr_ratio is not None and rr_ratio < 1.5 and ctx.action in ADD_LIKE_ACTIONS:
            ctx.action = "hold_no_add" if holding else "wait"
            ctx.reasons.append(f"风险收益比 {rr_ratio:.2f} 偏低，暂不加仓")
            ctx.flags.append("rr_below_one_five")
        if rr_downside is not None and rr_downside > 30 and ctx.action in {"add", "add_batch", "add_right_side"}:
            ctx.action = "add_on_pullback" if not holding else "hold_no_add"
            ctx.reasons.append(f"下行风险 {rr_downside:.1f}% 过高，禁止强加仓")
            ctx.flags.append("rr_downside_too_high")

    # -- Rule group: severe breakdown --
    def _check_severe_breakdown(self, ctx: _GateContext, mkt, evt, fund, holding: bool):
        if _is_severe_breakdown(mkt, evt, fund) and ctx.action in {"hold", "watchlist", "wait", "add_on_pullback"} and holding:
            ctx.action = "reduce_now"
            ctx.reasons.append("趋势/事件/基本面出现严重破坏，已转为减仓")
            ctx.flags.append("thesis_breakdown_detected")

    # -- Panic detection --
    def _detect_panic(self, user_question: str | None, decision_output: dict, card_pack: TradeDecisionCardPack) -> list[str]:
        text = " ".join(str(x or "") for x in [
            user_question or "",
            decision_output.get("decision_summary") or "",
            " ".join(decision_output.get("key_reasons") or []),
        ])
        if not text:
            return []
        matched = []
        for tok in PANIC_TOKENS_ZH:
            if tok in text:
                matched.append(tok)
        for tok in PANIC_TOKENS_EN:
            if tok in text.lower():
                matched.append(tok)
        if not matched or not _is_holding(card_pack):
            return []
        fund = card_pack.fundamental_valuation_card
        mkt = card_pack.market_trend_card
        if _is_severe_breakdown_for(fund) or _is_severe_breakdown_for(mkt) or _get_trend_break_level(mkt) in {"broken", "severe"}:
            return []
        return matched[:3]

    def _panic_result(self, original_action: str, panic: list[str]) -> RiskGateResult:
        return RiskGateResult(
            original_action=original_action, final_action="panic_blocked",
            blocked=True, downgraded=True,
            gate_reasons=["用户问题或决策摘要含恐慌/清仓意图，但基本面、趋势、仓位、风险收益均不支持卖出"],
            required_disclosures=["已识别为情绪化卖出请求并拦截；继续按原计划持有并观察"],
            risk_flags=["panic_sell_blocked"],
            action_constraints={"panic_match": panic},
            confidence_cap="low",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_trend_break_level(mkt: MarketTrendCard | None) -> str:
    if not mkt:
        return "unknown"
    return str(getattr(mkt, "trend_break_level", None) or "unknown")


def _get_fundamental_status(fund: FundamentalValuationCard | None) -> str:
    if not fund:
        return "unknown"
    return str(getattr(fund, "fundamental_status", None) or "unknown")


def _thesis_from_dict(thesis: dict[str, Any] | None):
    if not thesis or not isinstance(thesis, dict):
        from app.services.investment_thesis import DEFAULT_THESIS
        return DEFAULT_THESIS
    from app.services.investment_thesis import InvestmentThesis
    return InvestmentThesis(
        symbol=str(thesis.get("symbol") or ""),
        role=str(thesis.get("role") or "unknown"),
        risk_class=str(thesis.get("risk_class") or "unknown"),
        max_position_pct=float(thesis.get("max_position_pct") or 0),
        core_thesis=list(thesis.get("core_thesis") or []),
        sell_triggers=list(thesis.get("sell_triggers") or []),
        no_add_triggers=list(thesis.get("no_add_triggers") or []),
    )


def _is_fundamental_red(fund: FundamentalValuationCard | None) -> bool:
    if not fund:
        return False
    return getattr(fund, "fundamental_status", "unknown") == "red"


def _is_holding(card_pack: TradeDecisionCardPack) -> bool:
    facts = card_pack.account_facts
    if isinstance(facts, AccountFactSnapshot):
        return facts.is_holding
    if isinstance(facts, dict):
        pos = facts.get("position_context") or {}
        return bool(pos.get("has_position"))
    return False


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:
        return None
    return f


def _count_public_fallback(card_pack: TradeDecisionCardPack) -> int:
    count = 0
    for card in (card_pack.market_trend_card, card_pack.fundamental_valuation_card, card_pack.event_catalyst_card):
        if card is None:
            count += 1
        elif card.stance == CardStance.INSUFFICIENT_DATA:
            count += 1
        elif card.evidence_quality == "low" and card.score <= 1:
            count += 1
    return count


def _low_quality_evidence(card: Any) -> bool:
    if not card:
        return True
    if getattr(card, "stance", None) == CardStance.INSUFFICIENT_DATA:
        return True
    if getattr(card, "evidence_quality", None) == "low" and (getattr(card, "score", 0) or 0) <= 1:
        return True
    return False


def _is_weak_catalyst(evt: EventCatalystCard | None) -> bool:
    if not evt:
        return True
    if evt.catalyst_strength in ("weak", "no_catalyst"):
        return True
    if evt.score is not None and evt.score <= 1:
        return True
    if not evt.key_events and (evt.recent_news_count or 0) <= 1:
        return True
    return False


def _is_severe_breakdown(mkt, evt, fund) -> bool:
    if mkt and mkt.stance == CardStance.BEARISH and mkt.score is not None and mkt.score <= 1:
        return True
    if fund and fund.stance == CardStance.BEARISH and fund.score is not None and fund.score <= 1:
        return True
    if evt and evt.catalyst_strength == "weak" and evt.sentiment == "negative" and (evt.score or 0) <= 1:
        return True
    return False


def _is_severe_breakdown_for(card: Any) -> bool:
    if not card:
        return False
    return getattr(card, "stance", None) == CardStance.BEARISH and (getattr(card, "score", 0) or 0) <= 1


def _compute_confidence_cap(*, public_fallback_count, mkt, fund, rr, flags) -> str | None:
    flags_set = set(flags or [])
    if flags_set & {"panic_sell_blocked", "fundamental_red_action", "fundamental_red_blocked", "thesis_broken_detected"}:
        return "low"
    if public_fallback_count >= 3:
        return "low"
    if "weak_catalyst_downgrade" in flags_set:
        return "medium"
    if "insufficient_data" in flags_set:
        return "medium"
    return None


# ---------------------------------------------------------------------------
# Application helper
# ---------------------------------------------------------------------------

def apply_risk_gate(
    decision_output: dict[str, Any],
    card_pack: TradeDecisionCardPack,
    user_question: str | None = None,
) -> tuple[dict[str, Any], RiskGateResult]:
    """Run the gate, return (mutated decision_output, gate_result)."""
    gate = RiskGate()
    result = gate.evaluate(decision_output, card_pack, user_question=user_question)
    decision_output["action"] = result.final_action
    decision_output["risk_gate"] = result.to_dict()

    if result.gate_reasons:
        dl = list(decision_output.get("data_limitations") or [])
        for reason in result.gate_reasons:
            if reason and reason not in dl:
                dl.append(reason)
        decision_output["data_limitations"] = dl

    if result.risk_flags:
        rw = list(decision_output.get("review_warnings") or [])
        for flag in result.risk_flags:
            label = f"risk_gate:{flag}"
            if label not in rw:
                rw.append(label)
        decision_output["review_warnings"] = rw

    if result.confidence_cap:
        current = decision_output.get("confidence")
        new_conf = _clamp_confidence(current, result.confidence_cap)
        if new_conf != current:
            decision_output["confidence"] = new_conf

    return decision_output, result


def make_fail_safe_result(original_action: str, error: str) -> RiskGateResult:
    """Build a fail-safe RiskGateResult for when the gate itself raises."""
    return RiskGateResult(
        original_action=original_action,
        final_action="wait",
        blocked=False,
        downgraded=original_action != "wait",
        gate_reasons=["RiskGate 执行失败，已按保守策略降级"],
        required_disclosures=[f"RiskGate 内部错误: {error[:120]}"],
        risk_flags=["risk_gate_failed"],
        action_constraints={"fail_safe": True},
        confidence_cap="low",
        failed=True,
        error=error,
    )


__all__ = [
    "RiskGate", "RiskGateResult", "apply_risk_gate", "make_fail_safe_result",
    "RISK_GATE_ACTIONS", "ADD_LIKE_ACTIONS", "STRONG_ADD_ACTIONS",
    "HOLD_LIKE_ACTIONS", "EXIT_LIKE_ACTIONS",
]
