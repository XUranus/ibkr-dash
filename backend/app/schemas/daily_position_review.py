"""Daily position review request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class DailyReviewRequest(BaseModel):
    """Request to generate a daily position review."""
    report_date: str = ""


class DailyReviewResponse(BaseModel):
    """A daily position review result."""
    id: str
    report_date: str
    review_output: dict | str | None = None
    review_markdown: str | None = None
    summary: str | None = None
    account_conclusion: str | None = None
    attribution_summary: str | None = None
    major_contributors_analysis: list | None = None
    major_drags_analysis: list | None = None
    focus_symbol_analyses: list | None = None
    market_context: str | None = None
    risk_analysis: str | None = None
    tomorrow_watchlist: list | None = None
    operation_observation: str | None = None
    data_limitations: list[str] | None = None
    evidence_used: list[str] | None = None
    metadata: dict | None = None
    evidence_summary: dict | list | None = None
    run_trace: dict | list | None = None
    created_at: str | None = None


class DailyReviewDateListResponse(BaseModel):
    """List of available review dates."""
    items: list[str]


class DailyReviewHealthResponse(BaseModel):
    """Health check for the daily review agent."""
    status: str = "ok"
    agent_name: str = "daily_review"
    llm_configured: bool = False
    message: str | None = None
