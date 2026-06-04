"""Trade decision request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class TradeDecisionRequest(BaseModel):
    """Request to run a trade decision analysis."""
    symbol: str
    decision_type: str = "entry_decision"  # entry_decision | holding_decision
    question: str | None = None


class TradeDecisionResponse(BaseModel):
    """A trade decision result."""
    id: str
    decision_type: str
    symbol: str
    decision_output: dict | str | None = None
    metadata: dict | None = None
    evidence_summary: dict | None = None
    run_trace: dict | None = None
    created_at: str | None = None


class TradeDecisionListResponse(BaseModel):
    """List of trade decisions."""
    items: list[TradeDecisionResponse]


class TradeDecisionHealthResponse(BaseModel):
    """Health check for the trade decision agent."""
    status: str = "ok"
    agent_name: str = "trade_decision"
    llm_configured: bool = False
    message: str | None = None
