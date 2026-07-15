"""Account overview and snapshot schemas."""

from pydantic import BaseModel


class AccountDeltaMetric(BaseModel):
    """Day-over-day change for a metric."""
    amount_change: float | None = None
    percent_change: float | None = None


class AccountOverviewResponse(BaseModel):
    """Aggregated account overview with equity, cash, PnL, and deltas."""
    account_id: str
    report_date: str
    currency: str | None = None
    total_equity: float | None = None
    cash: float | None = None
    stock_value: float | None = None
    options_value: float | None = None
    funds_value: float | None = None
    crypto_value: float | None = None
    fifo_total_realized_pnl: float | None = None
    fifo_total_unrealized_pnl: float | None = None
    fifo_total_pnl: float | None = None
    fifo_total_pnl_return_rate: float | None = None  # P&L as % of net cost
    cnav_mtm: float | None = None
    cnav_twr: float | None = None
    total_equity_delta: AccountDeltaMetric | None = None
    fifo_total_realized_pnl_delta: AccountDeltaMetric | None = None
    fifo_total_unrealized_pnl_delta: AccountDeltaMetric | None = None
    fifo_total_pnl_delta: AccountDeltaMetric | None = None


class AccountSnapshot(BaseModel):
    """A single daily account snapshot row."""
    account_id: str
    report_date: str
    currency: str | None = None
    total_equity: float | None = None
    cash: float | None = None
    stock_value: float | None = None
    options_value: float | None = None
    funds_value: float | None = None
    crypto_value: float | None = None
    cnav_mtm: float | None = None
    cnav_twr: float | None = None
    fifo_total_realized_pnl: float | None = None
    fifo_total_unrealized_pnl: float | None = None


class AccountSnapshotListResponse(BaseModel):
    """Paginated list of account snapshots."""
    items: list[AccountSnapshot]
