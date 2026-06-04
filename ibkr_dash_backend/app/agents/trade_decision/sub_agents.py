"""Trade Decision sub-agent implementations.

Each sub-agent runs a bounded analysis using the ToolCallingRuntime
and produces a card with scores and evidence.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.runtime import AgentTool, ToolCallingRuntime
from app.agents.trade_decision.cards import (
    AccountFitCard,
    CardStance,
    EventCatalystCard,
    FundamentalValuationCard,
    MarketTrendCard,
    build_fallback_account_fit_card,
    build_fallback_event_card,
    build_fallback_fundamental_card,
    build_fallback_market_trend_card,
)
from app.agents.trade_decision.prompts import (
    ACCOUNT_FIT_PROMPT,
    EVENT_CATALYST_PROMPT,
    FUNDAMENTAL_PROMPT,
    MARKET_TREND_PROMPT,
)


def analyze_account_fit(
    llm_service: Any,
    account_facts: dict,
    symbol: str,
    decision_type: str,
) -> AccountFitCard:
    """Analyze account fit without MCP tools (deterministic + LLM)."""
    try:
        messages = [
            {"role": "system", "content": ACCOUNT_FIT_PROMPT},
            {"role": "user", "content": (
                f"Analyze account fit for {symbol} ({decision_type}).\n\n"
                f"Account facts:\n{json.dumps(account_facts, ensure_ascii=False, default=str)}\n\n"
                "Output strict JSON with: summary, score (0-20), stance, account_fit_level, "
                "deployable_liquidity, current_position_pct, max_suggested_position_pct, "
                "suggested_cash_amount, position_size_label, key_points, risks, review_warnings, "
                "historical_mistake_flags, data_limitations."
            )},
        ]
        runtime = ToolCallingRuntime(llm_service, max_rounds=1, agent_name="account_fit")
        result = runtime.run(messages=messages, tools=[], response_format={"type": "json_object"})
        payload = json.loads(result["content"])
        return AccountFitCard(
            symbol=symbol, decision_type=decision_type,
            summary=payload.get("summary", ""),
            score=payload.get("score", 0),
            max_score=payload.get("max_score", 20),
            stance=payload.get("stance", CardStance.INSUFFICIENT_DATA),
            account_fit_level=payload.get("account_fit_level", "unknown"),
            deployable_liquidity=payload.get("deployable_liquidity"),
            current_position_pct=payload.get("current_position_pct"),
            max_suggested_position_pct=payload.get("max_suggested_position_pct"),
            suggested_cash_amount=payload.get("suggested_cash_amount"),
            position_size_label=payload.get("position_size_label", "unknown"),
            key_points=payload.get("key_points", []),
            risks=payload.get("risks", []),
            review_warnings=payload.get("review_warnings", []),
            historical_mistake_flags=payload.get("historical_mistake_flags", []),
            evidence_quality="medium",
            data_limitations=payload.get("data_limitations", []),
        )
    except Exception as exc:
        return build_fallback_account_fit_card(symbol, decision_type, str(exc))


def analyze_market_trend(
    llm_service: Any,
    account_facts: dict,
    symbol: str,
    decision_type: str,
    mcp_tools: list[AgentTool] | None = None,
) -> MarketTrendCard:
    """Analyze market trend, optionally using MCP tools for public data."""
    try:
        tools = mcp_tools or []
        messages = [
            {"role": "system", "content": MARKET_TREND_PROMPT},
            {"role": "user", "content": (
                f"Analyze market trend for {symbol} ({decision_type}).\n\n"
                f"Account context:\n{json.dumps(account_facts, ensure_ascii=False, default=str)}\n\n"
                "Use available tools to get price, quote, and market data. "
                "Output strict JSON with: summary, score (0-15), stance, price_trend, "
                "relative_to_benchmark, recent_return_pct, volatility_summary, volume_signal, "
                "support_resistance, sector_view, key_points, risks, data_limitations."
            )},
        ]
        runtime = ToolCallingRuntime(llm_service, max_rounds=3, agent_name="market_trend")
        result = runtime.run(messages=messages, tools=tools, response_format={"type": "json_object"})
        payload = json.loads(result["content"])
        return MarketTrendCard(
            symbol=symbol, decision_type=decision_type,
            summary=payload.get("summary", ""),
            score=payload.get("score", 0),
            max_score=payload.get("max_score", 15),
            stance=payload.get("stance", CardStance.INSUFFICIENT_DATA),
            price_trend=payload.get("price_trend", "unknown"),
            relative_to_benchmark=payload.get("relative_to_benchmark"),
            recent_return_pct=payload.get("recent_return_pct"),
            volatility_summary=payload.get("volatility_summary", ""),
            volume_signal=payload.get("volume_signal"),
            support_resistance=payload.get("support_resistance", {}),
            sector_view=payload.get("sector_view"),
            key_points=payload.get("key_points", []),
            risks=payload.get("risks", []),
            evidence_quality="medium" if tools else "low",
            data_limitations=payload.get("data_limitations", []),
        )
    except Exception as exc:
        return build_fallback_market_trend_card(symbol, decision_type, str(exc))


def analyze_fundamental(
    llm_service: Any,
    account_facts: dict,
    symbol: str,
    decision_type: str,
    mcp_tools: list[AgentTool] | None = None,
) -> FundamentalValuationCard:
    """Analyze fundamentals and valuation, optionally using MCP tools."""
    try:
        tools = mcp_tools or []
        messages = [
            {"role": "system", "content": FUNDAMENTAL_PROMPT},
            {"role": "user", "content": (
                f"Analyze fundamentals and valuation for {symbol} ({decision_type}).\n\n"
                f"Account context:\n{json.dumps(account_facts, ensure_ascii=False, default=str)}\n\n"
                "Use available tools to get company info, financials, and valuation data. "
                "Output strict JSON with: summary, score (0-35), stance, company_name, market_cap, "
                "pe_ttm, forward_pe, revenue_growth_summary, profitability_summary, valuation_summary, "
                "peer_relative_note, key_points, risks, data_limitations."
            )},
        ]
        runtime = ToolCallingRuntime(llm_service, max_rounds=3, agent_name="fundamental")
        result = runtime.run(messages=messages, tools=tools, response_format={"type": "json_object"})
        payload = json.loads(result["content"])
        return FundamentalValuationCard(
            symbol=symbol, decision_type=decision_type,
            summary=payload.get("summary", ""),
            score=payload.get("score", 0),
            max_score=payload.get("max_score", 35),
            stance=payload.get("stance", CardStance.INSUFFICIENT_DATA),
            company_name=payload.get("company_name", ""),
            market_cap=payload.get("market_cap"),
            pe_ttm=payload.get("pe_ttm"),
            forward_pe=payload.get("forward_pe"),
            revenue_growth_summary=payload.get("revenue_growth_summary", ""),
            profitability_summary=payload.get("profitability_summary", ""),
            valuation_summary=payload.get("valuation_summary", ""),
            peer_relative_note=payload.get("peer_relative_note", ""),
            key_points=payload.get("key_points", []),
            risks=payload.get("risks", []),
            evidence_quality="medium" if tools else "low",
            data_limitations=payload.get("data_limitations", []),
        )
    except Exception as exc:
        return build_fallback_fundamental_card(symbol, decision_type, str(exc))


def analyze_event_catalyst(
    llm_service: Any,
    account_facts: dict,
    symbol: str,
    decision_type: str,
    mcp_tools: list[AgentTool] | None = None,
) -> EventCatalystCard:
    """Analyze event catalysts, optionally using MCP tools."""
    try:
        tools = mcp_tools or []
        messages = [
            {"role": "system", "content": EVENT_CATALYST_PROMPT},
            {"role": "user", "content": (
                f"Analyze event catalysts for {symbol} ({decision_type}).\n\n"
                f"Account context:\n{json.dumps(account_facts, ensure_ascii=False, default=str)}\n\n"
                "Use available tools to get news, events, and earnings data. "
                "Output strict JSON with: summary, score (0-5), stance, next_earnings_date, "
                "recent_news_count, key_events, sentiment, catalyst_strength, risk_events, "
                "key_points, risks, data_limitations."
            )},
        ]
        runtime = ToolCallingRuntime(llm_service, max_rounds=3, agent_name="event_catalyst")
        result = runtime.run(messages=messages, tools=tools, response_format={"type": "json_object"})
        payload = json.loads(result["content"])
        return EventCatalystCard(
            symbol=symbol, decision_type=decision_type,
            summary=payload.get("summary", ""),
            score=payload.get("score", 0),
            max_score=payload.get("max_score", 5),
            stance=payload.get("stance", CardStance.INSUFFICIENT_DATA),
            next_earnings_date=payload.get("next_earnings_date"),
            recent_news_count=payload.get("recent_news_count", 0),
            key_events=payload.get("key_events", []),
            sentiment=payload.get("sentiment", "neutral"),
            catalyst_strength=payload.get("catalyst_strength", "neutral"),
            risk_events=payload.get("risk_events", []),
            key_points=payload.get("key_points", []),
            risks=payload.get("risks", []),
            evidence_quality="medium" if tools else "low",
            data_limitations=payload.get("data_limitations", []),
        )
    except Exception as exc:
        return build_fallback_event_card(symbol, decision_type, str(exc))
