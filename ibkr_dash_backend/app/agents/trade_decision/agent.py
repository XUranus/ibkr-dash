"""Trade Decision agent.

Runs 4 sub-analyses in parallel via asyncio.gather, then composes the final decision.
"""

from __future__ import annotations

import asyncio
import json
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
)


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

    # Step 2: Run 4 sub-analyses in parallel using asyncio.gather with ThreadPoolExecutor
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

    # Step 3: Compose final decision
    system_prompt, prompt_metadata = resolve_runtime_prompt(
        prompt_service, "trade_decision_composer", SYSTEM_PROMPT,
    )
    user_prompt = _build_composer_prompt(
        symbol, decision_type, question, account_facts,
        account_fit_card, market_trend_card, fundamental_card, event_card,
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
    result = so_runtime.generate(messages, contract)

    if result.ok and result.payload:
        validated = _normalize_output(result.payload, symbol, decision_type)
    else:
        validated = _build_fallback_decision(symbol, decision_type, question)

    # Step 4: Save
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
            "account_facts": account_facts,
        },
        "raw_llm_response": result.raw_response if result.ok else "",
        "fallback_used": not result.ok,
        "prompt_metadata": {"trade_decision_composer": prompt_metadata},
    }
    saved = _save_decision(db, document)
    return saved


def _build_account_facts(db: Any, symbol: str, decision_type: str, question: str | None) -> dict:
    """Build account facts from DB. Placeholder for real implementation."""
    if hasattr(db, "build_account_facts"):
        snapshot = db.build_account_facts(decision_type, symbol, question)
        if hasattr(snapshot, "to_dict"):
            return snapshot.to_dict()
        return snapshot if isinstance(snapshot, dict) else {}
    return {
        "decision_type": decision_type,
        "symbol": symbol,
        "user_question": question,
        "account_context": {},
        "position_context": {},
        "trade_history_context": {},
        "review_context": {},
        "data_quality": {},
    }


def _build_composer_prompt(
    symbol: str, decision_type: str, question: str | None,
    account_facts: dict,
    account_fit_card: Any, market_trend_card: Any,
    fundamental_card: Any, event_card: Any,
) -> str:
    schema = {
        "symbol": symbol, "decision_type": decision_type,
        "overall_score": 0, "rating": "neutral", "action": "watchlist",
        "confidence": "low", "decision_summary": "...",
        "score_detail": {}, "position_advice": {}, "execution_plan": {},
        "key_reasons": [], "major_risks": [], "review_warnings": [],
        "data_limitations": [], "evidence_used": [],
    }
    return (
        f"Compose final trade decision for {symbol} ({decision_type}).\n"
        f"User question: {question or 'N/A'}\n\n"
        f"Account Fit Card:\n{json.dumps(account_fit_card.to_dict(), ensure_ascii=False, default=str)}\n\n"
        f"Market Trend Card:\n{json.dumps(market_trend_card.to_dict(), ensure_ascii=False, default=str)}\n\n"
        f"Fundamental/Valuation Card:\n{json.dumps(fundamental_card.to_dict(), ensure_ascii=False, default=str)}\n\n"
        f"Event Catalyst Card:\n{json.dumps(event_card.to_dict(), ensure_ascii=False, default=str)}\n\n"
        f"Account Facts:\n{json.dumps(account_facts, ensure_ascii=False, default=str)}\n\n"
        f"Output strict JSON matching this schema:\n{json.dumps(schema, ensure_ascii=False)}\n"
    )


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
    if hasattr(db, "save_decision"):
        return db.save_decision(document)
    return document
