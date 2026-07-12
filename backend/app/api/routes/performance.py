"""Performance endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user, get_db
from app.core.database import Database
from app.domains.performance.service import AccountPerformanceService
from app.domains.performance.schemas import PerformanceSeriesResponse, AccountPerformanceSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performance", tags=["performance"])


def _get_service(db: Database = Depends(get_db)) -> AccountPerformanceService:
    return AccountPerformanceService(db)


@router.get("/account/series", response_model=PerformanceSeriesResponse)
def get_account_performance_series(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    base_index: float = Query(default=100.0, gt=0),
    _user: str | None = Depends(get_current_user),
    service: AccountPerformanceService = Depends(_get_service),
) -> PerformanceSeriesResponse:
    """Get account performance series with TWR calculation."""
    try:
        return service.get_series(start_date=start_date, end_date=end_date, base_index=base_index)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/account/summary", response_model=AccountPerformanceSummary)
def get_account_performance_summary(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    base_index: float = Query(default=100.0, gt=0),
    _user: str | None = Depends(get_current_user),
    service: AccountPerformanceService = Depends(_get_service),
) -> AccountPerformanceSummary:
    """Get account performance summary."""
    try:
        return service.get_summary(start_date=start_date, end_date=end_date, base_index=base_index)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
