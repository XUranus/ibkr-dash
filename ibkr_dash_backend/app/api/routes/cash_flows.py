"""Cash flow list and summary endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_cash_flow_service, get_current_user
from app.schemas.cash_flows import CashFlowListResponse, CashFlowSummaryResponse
from app.services.cash_flow_service import CashFlowService

router = APIRouter(prefix="/cash-flows", tags=["cash-flows"])


@router.get("/summary", response_model=CashFlowSummaryResponse)
def get_cash_flow_summary(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    currency: str | None = Query(default=None),
    service: CashFlowService = Depends(get_cash_flow_service),
    _user: str | None = Depends(get_current_user),
) -> CashFlowSummaryResponse:
    """Return aggregated cash flow totals grouped by currency."""
    return service.get_summary(
        start_date=start_date,
        end_date=end_date,
        currency=currency,
    )


@router.get("", response_model=CashFlowListResponse)
def list_cash_flows(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    currency: str | None = Query(default=None),
    flow_direction: str | None = Query(default=None),
    sort_by: str = Query(default="date_time"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    service: CashFlowService = Depends(get_cash_flow_service),
    _user: str | None = Depends(get_current_user),
) -> CashFlowListResponse:
    """Return a paginated list of cash flow transactions."""
    try:
        return service.list_cash_flows(
            start_date=start_date,
            end_date=end_date,
            currency=currency,
            flow_direction=flow_direction,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
