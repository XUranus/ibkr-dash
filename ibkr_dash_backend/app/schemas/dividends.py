"""Dividend schemas (cash flows filtered to dividend-related flow types)."""

from pydantic import BaseModel

from app.schemas.common import PaginationInfo


class DividendItem(BaseModel):
    """A single dividend or withholding-tax cash flow record."""
    account_id: str
    currency: str | None = None
    symbol: str | None = None
    description: str | None = None
    date_time: str | None = None
    settle_date: str | None = None
    amount: float | None = None
    flow_type: str | None = None
    dividend_type: str | None = None
    transaction_id: str | None = None


class DividendListResponse(BaseModel):
    """Paginated dividend list."""
    items: list[DividendItem]
    pagination: PaginationInfo
