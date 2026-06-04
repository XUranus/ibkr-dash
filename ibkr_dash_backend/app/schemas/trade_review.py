"""Trade review request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class TradeReviewRequest(BaseModel):
    """Request to run a trade review."""
    symbol: str
    trade_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class TradeReviewResponse(BaseModel):
    """A trade review result."""
    id: str
    review_type: str
    symbol: str | None = None
    trade_id: str | None = None
    review_output: dict | str | None = None
    metadata: dict | None = None
    evidence_summary: dict | None = None
    run_trace: dict | None = None
    created_at: str | None = None


class TradeReviewListResponse(BaseModel):
    """List of trade reviews."""
    items: list[TradeReviewResponse]


class TradeReviewHealthResponse(BaseModel):
    """Health check for the trade review agent."""
    status: str = "ok"
    agent_name: str = "trade_review"
    llm_configured: bool = False
    message: str | None = None
