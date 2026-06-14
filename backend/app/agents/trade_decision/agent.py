"""Trade Decision agent.

Runs 5 sub-analyses in parallel via asyncio.gather, then composes the final
decision and applies the deterministic RiskGate.
"""

from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.agents.output_schemas import TradeDecisionOutput
from app.agents.prompt_runtime import resolve_runtime_prompt
from app.agents.structured_output import StructuredOutputContract, StructuredOutputRuntime
from app.agents.trade_decision.prompts import SYSTEM_PROMPT
from app.agents.trade_decision.sub_agents import (
    analyze_account_fit,
    analyze_event_catalyst,
    analyze_fundamental,
    analyze_market_trend,
    analyze_risk_reward,
)

logger = logging.getLogger(__name__)


async def analyze_trade(
    db: Any,
    llm_service: Any,
    symbol: str,
    decision_type: str = "entry_decision",
    *,
    question: str | None = None,
    mcp_tools: list | None = None,
    prompt_service: Any = None,
) -> dict:
    """Analyze a trade decision for a symbol.

    1. Build account facts from DB
    2. Run 4 sub-analyses in parallel (account_fit, market_trend, fundamental, event)
    3. Compose final decision with structured output

    Args:
        db: Database session or repository.
        llm_service: LLM service for text generation.
        symbol: Stock symbol to analyze.
        decision_type: "entry_decision" or "holding_decision".
        question: Optional user question context.
        mcp_tools: Optional MCP tools for public market data.
        prompt_service: Optional admin prompt override service.

    Returns:
        Saved decision document dict.
    """
    # Step 1: Build account facts
    account_facts = _build_account_facts(db, symbol, decision_type, question)

    # Step 2: Run 4 LLM sub-analyses in parallel
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=4) as executor:
        account_fit_task = loop.run_in_executor(
            executor, analyze_account_fit, llm_service, account_facts, symbol, decision_type,
        )
        market_trend_task = loop.run_in_executor(
            executor, analyze_market_trend, llm_service, account_facts, symbol, decision_type, mcp_tools,
        )
        fundamental_task = loop.run_in_executor(
            executor, analyze_fundamental, llm_service, account_facts, symbol, decision_type, mcp_tools,
        )
        event_task = loop.run_in_executor(
            executor, analyze_event_catalyst, llm_service, account_facts, symbol, decision_type, mcp_tools,
        )

        account_fit_card, market_trend_card, fundamental_card, event_card = await asyncio.gather(
            account_fit_task, market_trend_task, fundamental_task, event_task,
        )

    # Step 2b: Run deterministic risk/reward analysis (uses engines, no LLM)
    risk_reward_card = analyze_risk_reward(
        symbol=symbol,
        decision_type=decision_type,
        account_facts=account_facts,
        market_trend_card=market_trend_card,
        fundamental_card=fundamental_card,
    )

    # Step 3: Compose final decision
    system_prompt, prompt_metadata = resolve_runtime_prompt(
        prompt_service, "trade_decision_composer", SYSTEM_PROMPT,
    )
    user_prompt = _build_composer_prompt(
        symbol, decision_type, question, account_facts,
        account_fit_card, market_trend_card, fundamental_card, event_card, risk_reward_card,
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    contract = StructuredOutputContract(
        name="trade_decision",
        agent_name="trade_decision",
        node_name="compose",
        output_model=TradeDecisionOutput,
        schema_hint=TradeDecisionOutput.model_json_schema(),
        max_repair_attempts=1,
        repair_enabled=True,
        fallback_enabled=True,
        fallback_builder=lambda ctx, err, raw: _build_fallback_decision(symbol, decision_type, question),
    )
    so_runtime = StructuredOutputRuntime(llm_service)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, so_runtime.generate, messages, contract)

    if result.ok and result.payload:
        validated = _normalize_output(result.payload, symbol, decision_type)
    else:
        validated = _build_fallback_decision(symbol, decision_type, question)

    # Step 4: Apply Risk Gate (deterministic post-composer safety layer)
    from app.agents.trade_decision.cards import TradeDecisionCardPack
    from app.agents.trade_decision.risk_gate import apply_risk_gate, make_fail_safe_result
    from app.services.investment_thesis import get_thesis

    thesis = get_thesis(symbol)
    card_pack = TradeDecisionCardPack(
        decision_type=decision_type,
        symbol=symbol,
        account_facts=account_facts,
        account_fit_card=account_fit_card,
        market_trend_card=market_trend_card,
        fundamental_valuation_card=fundamental_card,
        event_catalyst_card=event_card,
        risk_reward_card=risk_reward_card,
        investment_thesis=thesis.to_dict(),
    )
    try:
        validated, gate_result = apply_risk_gate(validated, card_pack, user_question=question)
        logger.info("Risk gate applied: %s → %s (flags=%s)", gate_result.original_action, gate_result.final_action, gate_result.risk_flags)
    except Exception as exc:
        logger.error("Risk gate failed: %s", exc)
        gate_result = make_fail_safe_result(validated.get("action", "watchlist"), str(exc))
        validated["action"] = gate_result.final_action
        validated["risk_gate"] = gate_result.to_dict()

    # Step 5: Verify
    from app.agents.report_generator import verify_decision
    verification = verify_decision(validated)

    # Step 6: Generate bilingual reports
    from app.agents.report_generator import generate_trade_decision_report, save_report
    report_zh = generate_trade_decision_report(validated, symbol, lang="zh")
    report_en = generate_trade_decision_report(validated, symbol, lang="en")
    report_paths = save_report("trade_decision", symbol, report_zh, report_en, report_id=symbol)

    # Step 7: Save
    document = {
        **validated,
        "symbol": symbol,
        "decision_type": decision_type,
        "user_question": question,
        "evidence_pack": {
            "account_fit_card": account_fit_card.to_dict(),
            "market_trend_card": market_trend_card.to_dict(),
            "fundamental_valuation_card": fundamental_card.to_dict(),
            "event_catalyst_card": event_card.to_dict(),
            "risk_reward_card": risk_reward_card.to_dict(),
            "account_facts": account_facts,
            "investment_thesis": thesis.to_dict(),
        },
        "raw_llm_response": result.raw_response if result.ok else "",
        "fallback_used": not result.ok,
        "run_trace": result.trace if hasattr(result, "trace") else [],
        "prompt_metadata": {"trade_decision_composer": prompt_metadata},
        "verification": verification,
        "report_paths": report_paths,
        "report_zh": report_zh,
        "report_en": report_en,
    }
    saved = _save_decision(db, document)
    return saved


def _build_account_facts(db: Any, symbol: str, decision_type: str, question: str | None) -> dict:
    """Build account facts from SQLite database."""
    # Get latest account snapshot
    account = db.execute_one(
        "SELECT * FROM account_snapshots ORDER BY report_date DESC LIMIT 1"
    )
    report_date = account.get("report_date") if account else None

    # Get current position for the symbol
    position = db.execute_one(
        "SELECT * FROM position_snapshots WHERE symbol = ? ORDER BY report_date DESC LIMIT 1",
        (symbol,),
    )

    # Get trade history for the symbol
    trades = db.execute(
        "SELECT trade_date, buy_sell, quantity, trade_price, net_cash, fifo_pnl_realized "
        "FROM trade_records WHERE symbol = ? ORDER BY trade_date DESC LIMIT 20",
        (symbol,),
    )

    # Get all positions for context
    all_positions = db.execute(
        "SELECT symbol, position_value, percent_of_nav "
        "FROM position_snapshots WHERE report_date = ? ORDER BY position_value DESC LIMIT 50",
        (report_date,) if report_date else ("",),
    )

    total_equity = float(account.get("total_equity") or 0) if account else 0
    position_value = float(position.get("position_value") or 0) if position else 0

    return {
        "decision_type": decision_type,
        "symbol": symbol,
        "user_question": question,
        "account_context": {
            "total_equity": total_equity,
            "cash": float(account.get("cash") or 0) if account else 0,
            "stock_value": float(account.get("stock_value") or 0) if account else 0,
            "report_date": report_date,
        },
        "position_context": {
            "has_position": position is not None,
            "quantity": float(position.get("quantity") or 0) if position else 0,
            "mark_price": float(position.get("mark_price") or 0) if position else 0,
            "position_value": position_value,
            "percent_of_nav": float(position.get("percent_of_nav") or 0) if position else 0,
            "average_cost_price": float(position.get("average_cost_price") or 0) if position else 0,
            "total_unrealized_pnl": float(position.get("total_unrealized_pnl") or 0) if position else 0,
            "weight_pct": (position_value / total_equity * 100) if total_equity > 0 else 0,
        },
        "trade_history_context": {
            "trades": trades,
            "trade_count": len(trades),
            "total_realized_pnl": sum(float(t.get("fifo_pnl_realized") or 0) for t in trades),
        },
        "portfolio_context": {
            "positions": all_positions,
            "position_count": len(all_positions),
            "top_3_concentration": sum(float(p.get("percent_of_nav") or 0) for p in all_positions[:3]),
        },
        "data_quality": {
            "has_account_data": account is not None,
            "has_position_data": position is not None,
            "has_trade_data": len(trades) > 0,
        },
    }


def _build_composer_prompt(
    symbol: str, decision_type: str, question: str | None,
    account_facts: dict,
    account_fit_card: Any, market_trend_card: Any,
    fundamental_card: Any, event_card: Any, risk_reward_card: Any = None,
) -> str:
    schema = {
        "symbol": symbol, "decision_type": decision_type,
        "overall_score": 0, "rating": "neutral", "action": "watchlist",
        "confidence": "low", "decision_summary": "...",
        "score_detail": {}, "position_advice": {}, "execution_plan": {},
        "key_reasons": [], "major_risks": [], "review_warnings": [],
        "data_limitations": [], "evidence_used": [],
    }
    parts = [
        f"Compose final trade decision for {symbol} ({decision_type}).\n",
        f"User question: {question or 'N/A'}\n\n",
        f"Account Fit Card:\n{json.dumps(account_fit_card.to_dict(), ensure_ascii=False, default=str)}\n\n",
        f"Market Trend Card:\n{json.dumps(market_trend_card.to_dict(), ensure_ascii=False, default=str)}\n\n",
        f"Fundamental/Valuation Card:\n{json.dumps(fundamental_card.to_dict(), ensure_ascii=False, default=str)}\n\n",
        f"Event Catalyst Card:\n{json.dumps(event_card.to_dict(), ensure_ascii=False, default=str)}\n\n",
    ]
    if risk_reward_card:
        parts.append(f"Risk/Reward Card:\n{json.dumps(risk_reward_card.to_dict(), ensure_ascii=False, default=str)}\n\n")
    parts.append(f"Account Facts:\n{json.dumps(account_facts, ensure_ascii=False, default=str)}\n\n")
    parts.append(f"Output strict JSON matching this schema:\n{json.dumps(schema, ensure_ascii=False)}\n")
    return "".join(parts)


def _normalize_output(payload: dict, symbol: str, decision_type: str) -> dict:
    model = TradeDecisionOutput.model_validate({
        **payload,
        "symbol": payload.get("symbol") or symbol,
        "decision_type": payload.get("decision_type") or decision_type,
    })
    return model.model_dump()


def _build_fallback_decision(symbol: str, decision_type: str, question: str | None) -> dict:
    return {
        "symbol": symbol,
        "decision_type": decision_type,
        "overall_score": 0,
        "rating": "negative",
        "action": "watchlist",
        "confidence": "low",
        "decision_summary": "Analysis failed; recommend watching.",
        "score_detail": {},
        "position_advice": {},
        "execution_plan": {"should_act_now": False},
        "key_reasons": ["Insufficient data for reliable analysis"],
        "major_risks": ["Data insufficiency"],
        "review_warnings": [],
        "data_limitations": ["LLM output validation failed; using conservative fallback"],
        "evidence_used": [],
    }


def _save_decision(db: Any, document: dict) -> dict:
    """Save trade decision to database."""
    from uuid import uuid4
    decision_id = str(uuid4())
    db.upsert("trade_decisions", {
        "id": decision_id,
        "decision_type": document.get("decision_type", "entry_decision"),
        "symbol": document.get("symbol", ""),
        "decision_output": json.dumps(document, ensure_ascii=False, default=str),
        "metadata": json.dumps(document.get("metadata", {}), ensure_ascii=False, default=str),
        "evidence_summary": json.dumps(document.get("evidence_pack", {}), ensure_ascii=False, default=str),
        "run_trace": json.dumps(document.get("run_trace", []), ensure_ascii=False, default=str),
    }, conflict_cols=["id"])
    document["id"] = decision_id
    return document
