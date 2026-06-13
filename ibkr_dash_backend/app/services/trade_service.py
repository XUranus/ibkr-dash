"""Trade service: list and summarize trades from SQLite."""

from __future__ import annotations

from app.core.database import Database
from app.schemas.trades import TradeItem, TradeListResponse, TradeSummaryResponse
from app.utils.dates import parse_date
from app.utils.pagination import build_pagination, build_pagination_info

TRADE_SORT_FIELDS = {
    "date_time",
    "trade_date",
    "symbol",
    "quantity",
    "trade_price",
    "proceeds",
    "ib_commission",
    "fifo_pnl_realized",
}


class TradeService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list_trades(
        self,
        start_date: str | None,
        end_date: str | None,
        symbol: str | None,
        asset_class: str | None,
        buy_sell: str | None,
        sort_by: str,
        sort_order: str,
        page: int,
        page_size: int,
    ) -> TradeListResponse:
        """List trades with filtering, sorting, and pagination."""
        effective_start, effective_end = self._resolve_date_window(start_date, end_date)
        conditions, params = self._build_filters(effective_start, effective_end, symbol, asset_class, buy_sell)
        where_clause = " AND ".join(conditions) if conditions else "1=1"

        safe_sort_by = sort_by if sort_by in TRADE_SORT_FIELDS else "date_time"
        safe_sort_order = "ASC" if sort_order.lower() == "asc" else "DESC"

        count_row = self.db.execute_one(
            f"SELECT COUNT(*) AS cnt FROM trade_records WHERE {where_clause}",
            tuple(params),
        )
        total = int(count_row["cnt"]) if count_row else 0

        offset, limit = build_pagination(page, page_size)
        rows = self.db.execute(
            f"""
            SELECT account_id, trade_date, date_time, symbol, description,
                   asset_class, buy_sell, quantity, trade_price, trade_money,
                   proceeds, taxes, ib_commission, net_cash,
                   fifo_pnl_realized, exchange, order_type
            FROM trade_records
            WHERE {where_clause}
            ORDER BY {safe_sort_by} {safe_sort_order} NULLS LAST
            LIMIT ? OFFSET ?
            """,
            tuple(params) + (limit, offset),
        )

        items = [TradeItem(**row) for row in rows]
        return TradeListResponse(
            items=items,
            pagination=build_pagination_info(page, limit, total),
        )

    def summarize_trades(
        self,
        start_date: str | None,
        end_date: str | None,
        symbol: str | None,
        asset_class: str | None,
        buy_sell: str | None,
    ) -> TradeSummaryResponse:
        """Return aggregate trade statistics."""
        effective_start, effective_end = self._resolve_date_window(start_date, end_date)
        conditions, params = self._build_filters(effective_start, effective_end, symbol, asset_class, buy_sell)
        where_clause = " AND ".join(conditions) if conditions else "1=1"

        row = self.db.execute_one(
            f"""
            SELECT
                COUNT(*) AS trade_count,
                SUM(CASE WHEN buy_sell = 'BUY' THEN 1 ELSE 0 END) AS buy_count,
                SUM(CASE WHEN buy_sell = 'SELL' THEN 1 ELSE 0 END) AS sell_count,
                COALESCE(SUM(ib_commission), 0) AS total_commission,
                COALESCE(SUM(fifo_pnl_realized), 0) AS total_realized_pnl,
                COALESCE(SUM(proceeds), 0) AS total_proceeds,
                COUNT(DISTINCT symbol) AS symbols_count
            FROM trade_records
            WHERE {where_clause}
            """,
            tuple(params),
        )

        if row is None:
            return TradeSummaryResponse(
                trade_count=0, buy_count=0, sell_count=0,
                total_commission=0, total_realized_pnl=0, total_proceeds=0, symbols_count=0,
            )

        total_realized = float(row["total_realized_pnl"] or 0.0)

        # Fallback: compute realized PnL from FIFO when API zeroes fifo_pnl_realized
        # Only run FIFO when DB has no realized PnL AND there are trades
        trade_count = int(row["trade_count"] or 0)
        if abs(total_realized) < 0.01 and trade_count > 0:
            from app.utils.fifo import compute_fifo_cost_basis
            trades = self.db.execute(
                f"SELECT symbol, asset_class, trade_date, buy_sell, quantity, trade_price FROM trade_records WHERE {where_clause} ORDER BY symbol, trade_date ASC, date_time ASC",
                tuple(params),
            )
            fifo_map = compute_fifo_cost_basis(trades)
            total_realized = sum(d.get("realized_pnl", 0) for d in fifo_map.values())

        return TradeSummaryResponse(
            trade_count=int(row["trade_count"] or 0),
            buy_count=int(row["buy_count"] or 0),
            sell_count=int(row["sell_count"] or 0),
            total_commission=float(row["total_commission"] or 0.0),
            total_realized_pnl=total_realized,
            total_proceeds=float(row["total_proceeds"] or 0.0),
            symbols_count=int(row["symbols_count"] or 0),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_date_window(
        self, start_date: str | None, end_date: str | None
    ) -> tuple[str | None, str | None]:
        parsed_start = parse_date(start_date)
        parsed_end = parse_date(end_date)

        if parsed_start is None and parsed_end is None:
            return None, None

        effective_end = parsed_end
        if effective_end is None:
            effective_end = self._get_latest_trade_date()

        return (
            parsed_start.isoformat() if parsed_start else None,
            effective_end.isoformat() if effective_end else None,
        )

    def _get_latest_trade_date(self):
        row = self.db.execute_one(
            "SELECT trade_date FROM trade_records ORDER BY trade_date DESC LIMIT 1"
        )
        if not row or not row["trade_date"]:
            return None
        return parse_date(row["trade_date"])

    @staticmethod
    def _build_filters(
        start_date: str | None,
        end_date: str | None,
        symbol: str | None,
        asset_class: str | None,
        buy_sell: str | None,
    ) -> tuple[list[str], list]:
        conditions: list[str] = []
        params: list = []
        if start_date:
            conditions.append("trade_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("trade_date <= ?")
            params.append(end_date)
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        if asset_class:
            conditions.append("asset_class = ?")
            params.append(asset_class)
        if buy_sell:
            conditions.append("buy_sell = ?")
            params.append(buy_sell)
        return conditions, params
