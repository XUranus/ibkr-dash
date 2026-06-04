"""Trade Review agent.

Simplified from the original LangGraph-based implementation.
Single function that loads trade facts, builds evidence, calls LLM, and saves.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.output_schemas import TradeReviewOutput
from app.agents.prompt_runtime import resolve_runtime_prompt
from app.agents.trade_review.prompts import SYSTEM_PROMPT


async def review_trade(
    db: Any,
    llm_service: Any,
    symbol: str,
    trade_id: str | None = None,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    prompt_service: Any = None,
) -> dict:
    """Review a trade or symbol's trading history.

    1. Load trade facts from DB
    2. Build evidence pack
    3. Call LLM for analysis + scoring
    4. Validate and save

    Args:
        db: Database session or repository.
        llm_service: LLM service for text generation.
        symbol: Stock symbol to review.
        trade_id: Optional specific trade ID to review.
        start_date: Optional start date for symbol-level review.
        end_date: Optional end date for symbol-level review.
        prompt_service: Optional admin prompt override service.

    Returns:
        Saved review document dict.
    """
    from app.agents.evidence import build_trade_review_evidence_pack
    from app.agents.structured_output import StructuredOutputContract, StructuredOutputRuntime

    # Step 1: Load trade facts
    trade_facts = _load_trade_facts(db, symbol, trade_id, start_date, end_date)
    review_type = "single_trade_review" if trade_id else "symbol_level_review"

    # Step 2: Build evidence pack
    evidence_pack = build_trade_review_evidence_pack({
        "symbol": symbol,
        "review_type": review_type,
        "trade_facts": trade_facts,
        "performance_metrics": trade_facts.get("performance_metrics", {}),
        "price_context": trade_facts.get("price_context", {}),
        "external_events": trade_facts.get("external_events", {}),
        "data_quality": trade_facts.get("data_quality", {}),
    })

    # Step 3: Call LLM
    system_prompt, prompt_metadata = resolve_runtime_prompt(
        prompt_service, "trade_review_main", SYSTEM_PROMPT,
    )
    user_prompt = _build_user_prompt(symbol, review_type, trade_id, trade_facts)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    contract = StructuredOutputContract(
        name="trade_review",
        agent_name="trade_review",
        node_name="compose",
        output_model=TradeReviewOutput,
        schema_hint=TradeReviewOutput.model_json_schema(),
        max_repair_attempts=1,
        repair_enabled=True,
        fallback_enabled=True,
        fallback_builder=lambda ctx, err, raw: _build_fallback_review(symbol, review_type, trade_id),
    )
    so_runtime = StructuredOutputRuntime(llm_service)
    result = so_runtime.generate(messages, contract)

    if result.ok and result.payload:
        validated = _normalize_output(result.payload, symbol, review_type)
    else:
        validated = _build_fallback_review(symbol, review_type, trade_id)

    # Step 4: Save
    document = {
        **validated,
        "symbol": symbol,
        "trade_id": trade_id,
        "review_type": review_type,
        "evidence_pack": evidence_pack,
        "trade_facts": trade_facts,
        "raw_llm_response": result.raw_response if result.ok else "",
        "fallback_used": not result.ok,
        "prompt_metadata": {"trade_review_main": prompt_metadata},
    }
    saved = _save_review(db, document)
    return saved


def _load_trade_facts(
    db: Any, symbol: str, trade_id: str | None,
    start_date: str | None, end_date: str | None,
) -> dict:
    """Load trade facts from DB. Placeholder for real implementation."""
    if hasattr(db, "build_trade_review_evidence"):
        return db.build_trade_review_evidence(symbol, trade_id, start_date, end_date)
    return {
        "trades": [],
        "related_symbol_trades": [],
        "current_position": {},
        "first_buy_date": None,
        "last_trade_date": None,
        "is_currently_holding": False,
        "lifecycle_stage": "unknown",
        "reviewed_trade_id": trade_id,
        "performance_metrics": {},
        "price_context": {},
        "external_events": {},
        "data_quality": {},
    }


def _build_user_prompt(
    symbol: str, review_type: str, trade_id: str | None, trade_facts: dict,
) -> str:
    schema = {
        "symbol": symbol,
        "review_type": review_type,
        "overall_score": 0,
        "rating": "neutral",
        "summary": "...",
        "strengths": [],
        "weaknesses": [],
        "mistake_tags": [],
        "improvement_suggestions": [],
        "data_limitations": [],
        "evidence_used": [],
    }
    return (
        f"Review trade(s) for {symbol} ({review_type}).\n"
        f"Trade ID: {trade_id or 'N/A'}\n\n"
        f"Trade facts:\n{json.dumps(trade_facts, ensure_ascii=False, default=str)}\n\n"
        f"Evaluate entry quality, exit quality, position sizing, holding period, "
        f"risk control, and decision attribution.\n"
        f"Output strict JSON matching this schema:\n{json.dumps(schema, ensure_ascii=False)}\n"
    )


def _normalize_output(payload: dict, symbol: str, review_type: str) -> dict:
    model = TradeReviewOutput.model_validate({
        **payload,
        "symbol": payload.get("symbol") or symbol,
        "review_type": payload.get("review_type") or review_type,
    })
    return model.model_dump()


def _build_fallback_review(symbol: str, review_type: str, trade_id: str | None) -> dict:
    return {
        "symbol": symbol,
        "review_type": review_type,
        "overall_score": 50,
        "rating": "neutral",
        "summary": "Trade review failed; using conservative neutral assessment.",
        "strengths": [],
        "weaknesses": ["Insufficient data for reliable review"],
        "mistake_tags": [],
        "improvement_suggestions": ["Retry review when LLM output recovers"],
        "data_limitations": ["LLM output validation failed; using conservative fallback"],
        "evidence_used": [],
    }


def _save_review(db: Any, document: dict) -> dict:
    if hasattr(db, "save_review"):
        return db.save_review(document)
    return document
