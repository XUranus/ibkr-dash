"""Trade list and summary endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_trade_service
from app.schemas.trades import TradeListResponse, TradeSummaryResponse
from app.services.trade_service import TradeService

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("", response_model=TradeListResponse)
def list_trades(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
    asset_class: str | None = Query(default=None),
    buy_sell: str | None = Query(default=None),
    sort_by: str = Query(default="date_time"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    service: TradeService = Depends(get_trade_service),
) -> TradeListResponse:
    try:
        return service.list_trades(
            start_date=start_date,
            end_date=end_date,
            symbol=symbol,
            asset_class=asset_class,
            buy_sell=buy_sell,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/summary", response_model=TradeSummaryResponse)
def get_trade_summary(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
    asset_class: str | None = Query(default=None),
    buy_sell: str | None = Query(default=None),
    service: TradeService = Depends(get_trade_service),
) -> TradeSummaryResponse:
    try:
        return service.summarize_trades(
            start_date=start_date,
            end_date=end_date,
            symbol=symbol,
            asset_class=asset_class,
            buy_sell=buy_sell,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
