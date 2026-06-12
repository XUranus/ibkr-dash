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


class DividendCurrencySummaryItem(BaseModel):
    """Summary for a single currency."""
    currency: str | None = None
    record_count: int = 0
    dividend_count: int = 0
    withholding_tax_count: int = 0
    gross_dividend_amount: float = 0.0
    withholding_tax_amount: float = 0.0
    net_amount: float = 0.0


class DividendSummaryResponse(BaseModel):
    """Aggregated dividend summary."""
    record_count: int = 0
    dividend_count: int = 0
    withholding_tax_count: int = 0
    gross_dividend_amount: float | None = None
    withholding_tax_amount: float | None = None
    net_amount: float | None = None
    by_currency: list[DividendCurrencySummaryItem] = []
