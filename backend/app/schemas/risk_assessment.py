"""Risk assessment request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class RiskAssessmentRequest(BaseModel):
    """Request to run a risk assessment."""
    question: str | None = None


class RiskAssessmentResponse(BaseModel):
    """A risk assessment result."""
    id: str
    assessment_type: str
    risk_report: dict | str | None = None
    metadata: dict | None = None
    run_trace: dict | list | None = None
    created_at: str | None = None


class RiskAssessmentListResponse(BaseModel):
    """List of risk assessments."""
    items: list[RiskAssessmentResponse]


class RiskAssessmentHealthResponse(BaseModel):
    """Health check for the risk assessment agent."""
    status: str = "ok"
    agent_name: str = "risk_assessment"
    llm_configured: bool = False
    message: str | None = None
