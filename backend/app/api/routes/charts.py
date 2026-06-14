"""Chart data endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_chart_service, get_current_user
from app.schemas.charts import EquityCurveResponse, PerformanceCalendarResponse
from app.services.chart_service import ChartService

router = APIRouter(prefix="/charts", tags=["charts"])


@router.get("/equity-curve", response_model=EquityCurveResponse, response_model_exclude_none=True)
def get_equity_curve(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    service: ChartService = Depends(get_chart_service),
    _user: str | None = Depends(get_current_user),
) -> EquityCurveResponse:
    """Return time-series data for the portfolio equity curve chart."""
    try:
        return service.get_equity_curve(start_date=start_date, end_date=end_date)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/performance-calendar", response_model=PerformanceCalendarResponse, response_model_exclude_none=True)
def get_performance_calendar(
    view: str = Query(default="month"),
    anchor: str | None = Query(default=None),
    service: ChartService = Depends(get_chart_service),
    _user: str | None = Depends(get_current_user),
) -> PerformanceCalendarResponse:
    """Return calendar-heatmap data of daily/monthly portfolio performance."""
    try:
        return service.get_performance_calendar(view=view, anchor=anchor)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
