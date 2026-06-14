"""Position list, summary, and detail endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user, get_db, get_position_service
from app.core.database import Database
from app.schemas.positions import PositionDetailResponse, PositionListResponse, PositionSummaryResponse
from app.services.position_service import PositionService

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("/realtime")
def get_positions_realtime(
    db: Database = Depends(get_db),
    _user: str | None = Depends(get_current_user),
) -> dict:
    """Return positions with computed change percentages for the treemap.

    Uses unrealized PnL and cost basis to compute a change % when
    previous_day_change_percent is not available.
    """
    rows = db.execute(
        "SELECT symbol, description, asset_class, quantity, mark_price, "
        "position_value, percent_of_nav, cost_basis_money, "
        "total_unrealized_pnl, previous_day_change_percent "
        "FROM position_snapshots ORDER BY report_date DESC, position_value DESC LIMIT 200"
    )
    items = []
    for r in rows:
        change_pct = r.get("previous_day_change_percent")
        # Compute change % from unrealized PnL / position value
        if change_pct is None or change_pct == 0:
            pnl = r.get("total_unrealized_pnl") or 0
            value = r.get("position_value") or 0
            if value > 0:
                change_pct = round((pnl / value) * 100, 2)
            else:
                change_pct = 0
        items.append({
            "symbol": r.get("symbol"),
            "description": r.get("description"),
            "position_value": r.get("position_value"),
            "change_pct": change_pct,
        })
    return {"items": items, "count": len(items)}


@router.get("", response_model=PositionListResponse)
def list_positions(
    report_date: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
    asset_class: str | None = Query(default=None),
    include_summary: bool = Query(default=False),
    sort_by: str = Query(default="position_value"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    service: PositionService = Depends(get_position_service),
    _user: str | None = Depends(get_current_user),
) -> PositionListResponse:
    """Return a paginated list of portfolio positions."""
    try:
        return service.list_positions(
            report_date=report_date,
            symbol=symbol,
            asset_class=asset_class,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
            include_summary=include_summary,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/summary", response_model=PositionSummaryResponse)
def get_positions_summary(
    report_date: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
    asset_class: str | None = Query(default=None),
    service: PositionService = Depends(get_position_service),
    _user: str | None = Depends(get_current_user),
) -> PositionSummaryResponse:
    """Return aggregated position metrics such as total value and PnL."""
    try:
        return service.get_positions_summary(
            report_date=report_date,
            symbol=symbol,
            asset_class=asset_class,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/{symbol}", response_model=PositionDetailResponse)
def get_position_detail(
    symbol: str,
    asset_class: str | None = Query(default=None),
    service: PositionService = Depends(get_position_service),
    _user: str | None = Depends(get_current_user),
) -> PositionDetailResponse:
    """Return detailed information for a single position by symbol."""
    try:
        return service.get_position_detail(symbol=symbol, asset_class=asset_class)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
