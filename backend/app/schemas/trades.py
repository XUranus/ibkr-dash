"""Trade list and summary schemas."""

from pydantic import BaseModel

from app.schemas.common import PaginationInfo


class TradeItem(BaseModel):
    """A single trade record."""
    account_id: str
    trade_date: str | None = None
    date_time: str | None = None
    symbol: str | None = None
    description: str | None = None
    asset_class: str | None = None
    buy_sell: str | None = None
    quantity: float | None = None
    trade_price: float | None = None
    trade_money: float | None = None
    proceeds: float | None = None
    taxes: float | None = None
    ib_commission: float | None = None
    net_cash: float | None = None
    fifo_pnl_realized: float | None = None
    exchange: str | None = None
    order_type: str | None = None


class TradeListResponse(BaseModel):
    """Paginated trade list."""
    items: list[TradeItem]
    pagination: PaginationInfo


class TradeSummaryResponse(BaseModel):
    """Aggregated trade summary statistics."""
    trade_count: int
    buy_count: int
    sell_count: int
    total_commission: float
    total_realized_pnl: float
    total_proceeds: float
    symbols_count: int
