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


class CashFlowCurrencySummaryItem(BaseModel):
    """Summary for a single currency."""
    currency: str | None = None
    record_count: int = 0
    deposit_count: int = 0
    withdrawal_count: int = 0
    total_deposit_amount: float = 0.0
    total_withdrawal_amount: float = 0.0
    net_amount: float = 0.0


class CashFlowSummaryResponse(BaseModel):
    """Aggregated cash flow summary."""
    record_count: int = 0
    deposit_count: int = 0
    withdrawal_count: int = 0
    total_deposit_amount: float | None = None
    total_withdrawal_amount: float | None = None
    net_amount: float | None = None
    by_currency: list[CashFlowCurrencySummaryItem] = []
