"""Trade Review agent.

Simplified from the original LangGraph-based implementation.
Single function that loads trade facts, builds evidence, calls LLM, and saves.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.agents.output_schemas import TradeReviewOutput
from app.agents.prompt_runtime import resolve_runtime_prompt
from app.agents.trade_review.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


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
    # Run LLM call in thread executor to avoid blocking the event loop
    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, so_runtime.generate, messages, contract)

    if result.ok and result.payload:
        validated = _normalize_output(result.payload, symbol, review_type)
    else:
        validated = _build_fallback_review(symbol, review_type, trade_id)

    # Step 4: Verify
    from app.agents.report_generator import verify_review
    verification = verify_review(validated)

    # Step 5: Generate bilingual reports
    from app.agents.report_generator import generate_trade_review_report, save_report
    report_zh = generate_trade_review_report(validated, symbol, lang="zh")
    report_en = generate_trade_review_report(validated, symbol, lang="en")
    rid = trade_id or symbol
    report_paths = save_report("trade_review", symbol, report_zh, report_en, report_id=rid)

    # Step 6: Translate to Chinese
    review_output_zh = {}
    try:
        from app.services.translation_service import translate_trade_review_output
        import time as _time
        _t0 = _time.monotonic()
        loop2 = asyncio.get_running_loop()
        review_output_zh = await loop2.run_in_executor(
            None, translate_trade_review_output, llm_service, validated, "English", "Chinese",
        )
        logger.info("TradeReview translation completed: duration_ms=%d fields=%d", int((_time.monotonic() - _t0) * 1000), len(review_output_zh) if review_output_zh else 0)
    except Exception:
        logger.debug("TradeReview translation skipped", exc_info=True)

    # Step 7: Save
    document = {
        **validated,
        "symbol": symbol,
        "trade_id": trade_id,
        "review_type": review_type,
        "evidence_pack": evidence_pack,
        "trade_facts": trade_facts,
        "raw_llm_response": result.raw_response if result.ok else "",
        "fallback_used": not result.ok,
        "run_trace": result.trace if hasattr(result, "trace") else [],
        "prompt_metadata": {"trade_review_main": prompt_metadata},
        "verification": verification,
        "report_paths": report_paths,
        "report_zh": report_zh,
        "report_en": report_en,
        "review_output_zh": review_output_zh,
    }
    saved = _save_review(db, document)
    # Push notification
    try:
        from app.services.notification_service import notify_trade_review_completed
        notify_trade_review_completed(saved)
    except Exception:
        logger.debug("TradeReview notification skipped", exc_info=True)
    return saved


def _load_trade_facts(
    db: Any, symbol: str, trade_id: str | None,
    start_date: str | None, end_date: str | None,
) -> dict:
    """Load trade facts from SQLite database."""
    # Get trades for the symbol
    conditions = ["symbol = ?"]
    params: list = [symbol]
    if trade_id:
        conditions.append("trade_id = ?")
        params.append(trade_id)
    if start_date:
        conditions.append("trade_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("trade_date <= ?")
        params.append(end_date)

    where = " AND ".join(conditions)
    trades = db.execute(
        f"SELECT * FROM trade_records WHERE {where} ORDER BY trade_date DESC LIMIT 100",
        tuple(params),
    )

    # Get current position
    position = db.execute_one(
        "SELECT * FROM position_snapshots WHERE symbol = ? ORDER BY report_date DESC LIMIT 1",
        (symbol,),
    )

    # Calculate lifecycle facts
    buy_trades = [t for t in trades if t.get("buy_sell") == "BUY"]
    sell_trades = [t for t in trades if t.get("buy_sell") == "SELL"]
    total_bought = sum(float(t.get("quantity") or 0) for t in buy_trades)
    total_sold = sum(abs(float(t.get("quantity") or 0)) for t in sell_trades)
    total_commission = sum(float(t.get("ib_commission") or 0) for t in trades)
    realized_pnl = sum(float(t.get("fifo_pnl_realized") or 0) for t in trades)

    return {
        "trades": trades,
        "related_symbol_trades": [],
        "current_position": position or {},
        "first_buy_date": buy_trades[-1].get("trade_date") if buy_trades else None,
        "last_trade_date": trades[0].get("trade_date") if trades else None,
        "is_currently_holding": position is not None and float(position.get("quantity") or 0) > 0,
        "lifecycle_stage": "open" if position and float(position.get("quantity") or 0) > 0 else "closed",
        "reviewed_trade_id": trade_id,
        "performance_metrics": {
            "total_bought": total_bought,
            "total_sold": total_sold,
            "total_commission": total_commission,
            "realized_pnl": realized_pnl,
            "trade_count": len(trades),
            "buy_count": len(buy_trades),
            "sell_count": len(sell_trades),
        },
        "price_context": {},
        "external_events": {},
        "data_quality": {
            "has_trades": len(trades) > 0,
            "has_position": position is not None,
        },
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
    """Save trade review to database."""
    from uuid import uuid4
    review_id = str(uuid4())
    review_output_zh = document.pop("review_output_zh", {})
    db.upsert("trade_reviews", {
        "id": review_id,
        "review_type": document.get("review_type", "symbol_level_review"),
        "symbol": document.get("symbol", ""),
        "trade_id": document.get("trade_id"),
        "review_output": json.dumps(document, ensure_ascii=False, default=str),
        "review_output_zh": json.dumps(review_output_zh, ensure_ascii=False, default=str) if review_output_zh else None,
        "metadata": json.dumps(document.get("metadata", {}), ensure_ascii=False, default=str),
        "evidence_summary": json.dumps(document.get("evidence_pack", {}), ensure_ascii=False, default=str),
        "run_trace": json.dumps(document.get("run_trace", []), ensure_ascii=False, default=str),
    }, conflict_cols=["id"])
    document["id"] = review_id
    return document
