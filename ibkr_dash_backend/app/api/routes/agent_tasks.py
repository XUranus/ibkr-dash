"""Agent task management endpoints.

Provides endpoints for running agents in the background and tracking their status.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_agent_task_service, get_llm_service
from app.core.rate_limit import check_llm_rate_limit
from app.services.agent_services import AgentTaskService
from app.services.llm_service import LLMService

router = APIRouter(prefix="/agent", tags=["agent"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class AgentRunRequest(BaseModel):
    """Request to run an agent."""
    agent_name: str = Field(description="Agent to run: daily_review, trade_decision, trade_review, risk_assessment")
    symbol: str | None = None
    trade_id: str | None = None
    report_date: str | None = None
    question: str | None = None
    decision_type: str | None = None  # entry_decision | holding_decision
    start_date: str | None = None
    end_date: str | None = None


class AgentTaskResponse(BaseModel):
    """Agent task status."""
    id: str
    agent_name: str
    status: str
    progress: dict | None = None
    result: dict | None = None
    error: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/run", response_model=AgentTaskResponse)
def run_agent(
    request: AgentRunRequest,
    llm_service: LLMService = Depends(get_llm_service),
    task_service: AgentTaskService = Depends(get_agent_task_service),
    _rate: None = Depends(check_llm_rate_limit),
) -> AgentTaskResponse:
    """Run an agent in the background and return a task ID for tracking."""
    agent_name = request.agent_name
    db = task_service.db

    if agent_name == "daily_review":
        from app.agents.daily_review.agent import generate_daily_review
        task_id = task_service.run_in_background(
            "daily_review",
            generate_daily_review,
            db, llm_service, request.report_date or "",
        )

    elif agent_name == "trade_decision":
        if not request.symbol:
            raise HTTPException(status_code=400, detail="symbol is required for trade_decision")
        from app.agents.trade_decision.agent import analyze_trade
        task_id = task_service.run_in_background(
            "trade_decision",
            analyze_trade,
            db, llm_service, request.symbol,
            decision_type=request.decision_type or "entry_decision",
            question=request.question,
        )

    elif agent_name == "trade_review":
        if not request.symbol:
            raise HTTPException(status_code=400, detail="symbol is required for trade_review")
        from app.agents.trade_review.agent import review_trade
        task_id = task_service.run_in_background(
            "trade_review",
            review_trade,
            db, llm_service, request.symbol,
            trade_id=request.trade_id,
            start_date=request.start_date,
            end_date=request.end_date,
        )

    elif agent_name == "risk_assessment":
        from app.agents.risk_assessment.agent import assess_risk
        task_id = task_service.run_in_background(
            "risk_assessment",
            assess_risk,
            db, llm_service,
            question=request.question,
        )

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent: {agent_name}. Must be one of: daily_review, trade_decision, trade_review, risk_assessment",
        )

    task = task_service.get_task(task_id)
    return AgentTaskResponse(**task) if task else AgentTaskResponse(
        id=task_id, agent_name=agent_name, status="pending",
    )


@router.get("/tasks", response_model=list[AgentTaskResponse])
def list_tasks(
    agent_name: str | None = Query(default=None),
    task_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    task_service: AgentTaskService = Depends(get_agent_task_service),
) -> list[AgentTaskResponse]:
    """List agent tasks with optional filters."""
    tasks = task_service.list_tasks(agent_name=agent_name, status=task_status, limit=limit)
    return [AgentTaskResponse(**t) for t in tasks]


@router.get("/tasks/{task_id}", response_model=AgentTaskResponse)
def get_task(
    task_id: str,
    task_service: AgentTaskService = Depends(get_agent_task_service),
) -> AgentTaskResponse:
    """Get a specific agent task by ID."""
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return AgentTaskResponse(**task)


@router.post("/tasks/{task_id}/cancel", response_model=AgentTaskResponse)
def cancel_task(
    task_id: str,
    task_service: AgentTaskService = Depends(get_agent_task_service),
) -> AgentTaskResponse:
    """Cancel a running agent task."""
    success = task_service.cancel_task(task_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Task not found or already completed/failed/cancelled",
        )
    task = task_service.get_task(task_id)
    return AgentTaskResponse(**task) if task else AgentTaskResponse(
        id=task_id, agent_name="", status="cancelled",
    )
