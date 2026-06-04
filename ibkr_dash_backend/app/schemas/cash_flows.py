"""Cash flow schemas."""

from pydantic import BaseModel

from app.schemas.common import PaginationInfo


class CashFlowItem(BaseModel):
    """A single cash flow record."""
    account_id: str
    currency: str | None = None
    symbol: str | None = None
    description: str | None = None
    date_time: str | None = None
    settle_date: str | None = None
    amount: float | None = None
    amount_in_base: float | None = None
    flow_type: str | None = None
    dividend_type: str | None = None
    transaction_id: str | None = None


class CashFlowListResponse(BaseModel):
    """Paginated cash flow list."""
    items: list[CashFlowItem]
    pagination: PaginationInfo
