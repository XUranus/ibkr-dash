"""Admin agent evaluation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_db
from app.core.database import Database
from app.services.eval_simulation_service import EvalSimulationService

router = APIRouter(prefix="/admin/agent-eval", tags=["admin-agent-eval"])


def _get_service(db: Database = Depends(get_db)) -> EvalSimulationService:
    return EvalSimulationService(db)


@router.get("/simulations")
def list_simulations(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user: str | None = Depends(get_current_user),
    svc: EvalSimulationService = Depends(_get_service),
) -> dict:
    """List evaluation simulations."""
    return svc.list_simulations(limit=limit, offset=offset)


@router.get("/simulations/{replay_id}")
def get_simulation(
    replay_id: str,
    _user: str | None = Depends(get_current_user),
    svc: EvalSimulationService = Depends(_get_service),
) -> dict:
    """Get a specific simulation."""
    result = svc.get_simulation(replay_id)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Simulation not found")
    return result


@router.get("/stats")
def get_eval_stats(
    days: int = Query(default=30, ge=1, le=365),
    _user: str | None = Depends(get_current_user),
    svc: EvalSimulationService = Depends(_get_service),
) -> dict:
    """Get per-agent evaluation statistics."""
    items = svc.get_agent_stats(days=days)
    return {"items": items}
