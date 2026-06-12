"""Position service: list, summary, and detail queries against SQLite."""

from __future__ import annotations

from app.core.database import Database
from app.utils.fifo import compute_fifo_cost_basis
from app.schemas.positions import (
    PositionAssetDistributionItem,
    PositionConcentrationItem,
    PositionDetailBar,
    PositionDetailResponse,
    PositionDetailTradeMarker,
    PositionItem,
    PositionListResponse,
    PositionSummaryResponse,
)
from app.utils.pagination import build_pagination, build_pagination_info

POSITION_SORT_FIELDS = {
    "position_value",
    "percent_of_nav",
    "total_unrealized_pnl",
    "total_realized_pnl",
    "average_cost_price",
    "previous_day_change_percent",
    "symbol",
    "quantity",
}

POSITION_COLUMNS = """
    account_id, report_date, symbol, description, asset_class,
    quantity, mark_price, position_value, percent_of_nav,
    average_cost_price, cost_basis_money, total_realized_pnl,
    total_unrealized_pnl, total_unrealized_pnl AS unrealized_pnl_raw,
    previous_day_change_percent
"""


class PositionService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list_positions(
        self,
        report_date: str | None,
        symbol: str | None,
        asset_class: str | None,
        sort_by: str,
        sort_order: str,
        page: int,
        page_size: int,
        include_summary: bool = False,
    ) -> PositionListResponse:
        """List positions with filtering, sorting, and pagination."""
        effective_report_date = report_date or self._get_latest_report_date()
        if effective_report_date is None:
            empty_pagination = build_pagination_info(page, page_size, 0)
            return PositionListResponse(items=[], pagination=empty_pagination)

        # Validate sort field
        safe_sort_by = sort_by if sort_by in POSITION_SORT_FIELDS else "position_value"
        safe_sort_order = "ASC" if sort_order.lower() == "asc" else "DESC"

        # Build WHERE clause
        conditions = ["report_date = ?"]
        params: list = [effective_report_date]
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        if asset_class:
            conditions.append("asset_class = ?")
            params.append(asset_class)
        where_clause = " AND ".join(conditions)

        # Count total
        count_row = self.db.execute_one(
            f"SELECT COUNT(*) AS cnt FROM position_snapshots WHERE {where_clause}",
            tuple(params),
        )
        total = int(count_row["cnt"]) if count_row else 0

        # Fetch page
        offset, limit = build_pagination(page, page_size)
        rows = self.db.execute(
            f"""
            SELECT {POSITION_COLUMNS},
                   cost_basis_money,
                   COALESCE(total_realized_pnl, 0) AS total_realized_pnl
            FROM position_snapshots
            WHERE {where_clause}
            ORDER BY {safe_sort_by} {safe_sort_order} NULLS LAST
            LIMIT ? OFFSET ?
            """,
            tuple(params) + (limit, offset),
        )

        # Backfill zero financial fields with latest non-zero historical values
        self._backfill_zero_fields(rows)

        # Enrich with realized PnL from trades if missing
        self._enrich_realized_pnl(rows, effective_report_date)

        items = [self._row_to_position_item(row) for row in rows]

        summary = None
        if include_summary:
            summary = self._build_summary(effective_report_date, symbol, asset_class, rows)

        return PositionListResponse(
            items=items,
            pagination=build_pagination_info(page, limit, total),
            summary=summary,
        )

    def get_positions_summary(
        self,
        report_date: str | None,
        symbol: str | None,
        asset_class: str | None,
    ) -> PositionSummaryResponse:
        """Return aggregated position summary for a given report date."""
        effective_report_date = report_date or self._get_latest_report_date()
        if effective_report_date is None:
            return PositionSummaryResponse(top_positions=[], asset_distribution=[])

        conditions = ["report_date = ?"]
        params: list = [effective_report_date]
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        if asset_class:
            conditions.append("asset_class = ?")
            params.append(asset_class)
        where_clause = " AND ".join(conditions)

        # Top 5 positions by value
        top_rows = self.db.execute(
            f"""
            SELECT symbol, description, asset_class, position_value, percent_of_nav
            FROM position_snapshots
            WHERE {where_clause}
            ORDER BY position_value DESC NULLS LAST
            LIMIT 5
            """,
            tuple(params),
        )

        # Aggregations
        agg = self.db.execute_one(
            f"""
            SELECT
                COUNT(*) AS total_positions,
                COALESCE(SUM(position_value), 0) AS total_position_value,
                COALESCE(SUM(cost_basis_money), 0) AS total_cost_basis_money,
                COALESCE(SUM(total_realized_pnl), 0) AS total_realized_pnl,
                COALESCE(SUM(total_unrealized_pnl), 0) AS total_unrealized_pnl
            FROM position_snapshots
            WHERE {where_clause}
            """,
            tuple(params),
        )

        # Asset distribution
        dist_rows = self.db.execute(
            f"""
            SELECT
                COALESCE(asset_class, 'UNKNOWN') AS asset_class,
                COALESCE(SUM(position_value), 0) AS position_value,
                COUNT(*) AS positions_count
            FROM position_snapshots
            WHERE {where_clause}
            GROUP BY COALESCE(asset_class, 'UNKNOWN')
            ORDER BY position_value DESC
            """,
            tuple(params),
        )

        top_positions = [
            PositionConcentrationItem(
                symbol=r.get("symbol"),
                description=r.get("description"),
                asset_class=r.get("asset_class"),
                position_value=float(r.get("position_value") or 0.0),
                percent_of_nav=r.get("percent_of_nav"),
            )
            for r in top_rows
        ]

        asset_distribution = [
            PositionAssetDistributionItem(
                asset_class=r["asset_class"] if r["asset_class"] != "UNKNOWN" else None,
                position_value=float(r.get("position_value") or 0.0),
                positions_count=int(r.get("positions_count") or 0),
            )
            for r in dist_rows
        ]

        return PositionSummaryResponse(
            report_date=effective_report_date,
            total_positions=int(agg["total_positions"]) if agg else 0,
            total_position_value=float(agg["total_position_value"]) if agg else 0.0,
            total_cost_basis_money=float(agg["total_cost_basis_money"]) if agg else 0.0,
            total_realized_pnl=float(agg["total_realized_pnl"]) if agg else 0.0,
            total_unrealized_pnl=float(agg["total_unrealized_pnl"]) if agg else 0.0,
            total_fifo_pnl=(
                float(agg["total_realized_pnl"] or 0) + float(agg["total_unrealized_pnl"] or 0)
                if agg else 0.0
            ),
            top_positions=top_positions,
            asset_distribution=asset_distribution,
        )

    def get_position_detail(
        self,
        symbol: str,
        asset_class: str | None,
    ) -> PositionDetailResponse:
        """Return position detail with OHLC bars and trade markers."""
        # Fetch price history bars
        price_conditions = ["symbol = ?"]
        price_params: list = [symbol]
        if asset_class:
            price_conditions.append("asset_class = ?")
            price_params.append(asset_class)
        price_where = " AND ".join(price_conditions)

        price_rows = self.db.execute(
            f"""
            SELECT report_date, open_price, high_price, low_price, close_price
            FROM price_history
            WHERE {price_where}
            ORDER BY report_date ASC
            """,
            tuple(price_params),
        )

        # Fetch position snapshots as fallback for bars (no open_price column)
        position_rows = self.db.execute(
            """
            SELECT report_date, mark_price, quantity, description, asset_class
            FROM position_snapshots
            WHERE symbol = ?
            ORDER BY report_date ASC
            """,
            (symbol,),
        )

        # Fetch trade markers
        trade_conditions = ["symbol = ?"]
        trade_params: list = [symbol]
        if asset_class:
            trade_conditions.append("asset_class = ?")
            trade_params.append(asset_class)
        trade_where = " AND ".join(trade_conditions)

        trade_rows = self.db.execute(
            f"""
            SELECT trade_date, date_time, buy_sell, quantity, trade_price, fifo_pnl_realized
            FROM trade_records
            WHERE {trade_where}
            ORDER BY trade_date ASC, date_time ASC
            """,
            tuple(trade_params),
        )

        # Build trade price lookup by date
        trade_prices_by_date: dict[str, list[float]] = {}
        for tr in trade_rows:
            td = tr.get("trade_date")
            tp = tr.get("trade_price")
            if td and tp is not None:
                trade_prices_by_date.setdefault(str(td), []).append(float(tp))

        # Build bars
        bars: list[PositionDetailBar] = []
        if price_rows:
            for pr in price_rows:
                rd = pr["report_date"]
                op = pr.get("open_price")
                cp = pr.get("close_price")
                hp = pr.get("high_price")
                lp = pr.get("low_price")
                trade_points = trade_prices_by_date.get(str(rd), [])
                if trade_points:
                    numeric_points = [
                        v for v in [
                            float(op) if op is not None else None,
                            float(cp) if cp is not None else None,
                            float(hp) if hp is not None else None,
                            float(lp) if lp is not None else None,
                            *trade_points,
                        ]
                        if v is not None
                    ]
                    if numeric_points:
                        hp = max(numeric_points)
                        lp = min(numeric_points)
                bars.append(PositionDetailBar(
                    report_date=rd,
                    open_price=op,
                    high_price=hp,
                    low_price=lp,
                    close_price=cp,
                    quantity=None,
                ))
        else:
            for pr in position_rows:
                cp = pr.get("mark_price")
                pts = [
                    v for v in [
                        float(cp) if cp is not None else None,
                        *trade_prices_by_date.get(str(pr.get("report_date")), []),
                    ]
                    if v is not None
                ]
                bars.append(PositionDetailBar(
                    report_date=pr["report_date"],
                    open_price=None,
                    high_price=max(pts) if pts else None,
                    low_price=min(pts) if pts else None,
                    close_price=cp,
                    quantity=pr.get("quantity"),
                ))

        # Build trade markers
        trades = [
            PositionDetailTradeMarker(
                trade_date=tr.get("trade_date"),
                date_time=tr.get("date_time"),
                buy_sell=tr.get("buy_sell"),
                quantity=tr.get("quantity"),
                trade_price=tr.get("trade_price"),
                fifo_pnl_realized=tr.get("fifo_pnl_realized"),
            )
            for tr in trade_rows
        ]

        # Derive metadata
        metadata_source = (
            price_rows[-1] if price_rows
            else (position_rows[-1] if position_rows else (trade_rows[-1] if trade_rows else {}))
        )

        return PositionDetailResponse(
            symbol=metadata_source.get("symbol", symbol),
            description=metadata_source.get("description"),
            asset_class=metadata_source.get("asset_class", asset_class),
            bars=bars,
            trades=trades,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_latest_report_date(self) -> str | None:
        row = self.db.execute_one(
            "SELECT report_date FROM position_snapshots ORDER BY report_date DESC LIMIT 1"
        )
        return row["report_date"] if row else None

    def _backfill_zero_fields(self, rows: list[dict]) -> None:
        """Backfill zero financial fields with computed or historical values.

        IBKR real-time API zeroes out cost_basis_money, fifo_pnl_unrealized,
        and average_cost_price. This method:
        1. Looks up the latest non-zero historical value from position_snapshots
        2. Falls back to FIFO cost basis computed from trade records
        """
        fields_to_backfill = [
            "cost_basis_money",
            "total_unrealized_pnl",
            "fifo_pnl_unrealized",
            "average_cost_price",
        ]
        _EPSILON = 0.01

        # Collect symbols that need backfilling
        symbols_to_fix: set[str] = set()
        for row in rows:
            sym = row.get("symbol")
            if sym and any(abs(float(row.get(f) or 0)) < _EPSILON for f in fields_to_backfill):
                symbols_to_fix.add(sym)

        if not symbols_to_fix:
            return

        # Strategy 1: look up latest non-zero historical values
        placeholders = ",".join("?" for _ in symbols_to_fix)
        backfill_rows = self.db.execute(
            f"""
            SELECT symbol, cost_basis_money, total_unrealized_pnl,
                   fifo_pnl_unrealized, average_cost_price, quantity, mark_price
            FROM (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY report_date DESC) AS rn
                FROM position_snapshots
                WHERE symbol IN ({placeholders}) AND cost_basis_money > 0
            )
            WHERE rn = 1
            """,
            tuple(symbols_to_fix),
        )
        backfill_map: dict[str, dict] = {r["symbol"]: r for r in backfill_rows}

        # Strategy 2: compute FIFO cost basis from trade records
        still_missing = symbols_to_fix - set(backfill_map.keys())
        fifo_map: dict[str, dict] = {}
        if still_missing:
            fifo_map = self._compute_fifo_cost_basis(still_missing)

        # Apply backfill
        for row in rows:
            sym = row.get("symbol")
            if not sym:
                continue

            cost = float(row.get("cost_basis_money") or 0)
            qty = float(row.get("quantity") or 0)
            value = float(row.get("position_value") or 0)

            # Backfill cost_basis_money
            if cost == 0:
                if sym in backfill_map and backfill_map[sym].get("cost_basis_money"):
                    cost = float(backfill_map[sym]["cost_basis_money"])
                    row["cost_basis_money"] = cost
                elif sym in fifo_map:
                    fifo_cost = fifo_map[sym]["cost_basis"]
                    fifo_qty = fifo_map[sym].get("total_qty", 0)
                    # Scale if FIFO quantity doesn't match actual position
                    # (happens when trade history is incomplete)
                    if fifo_qty > 0 and qty > 0 and abs(fifo_qty - qty) > 0.01:
                        cost = fifo_cost * (qty / fifo_qty)
                    else:
                        cost = fifo_cost
                    row["cost_basis_money"] = cost

            # Backfill average_cost_price
            if float(row.get("average_cost_price") or 0) == 0 and cost > 0 and qty > 0:
                row["average_cost_price"] = cost / qty

            # Backfill unrealized PnL
            if float(row.get("total_unrealized_pnl") or 0) == 0 and cost > 0:
                unrealized = value - cost
                row["total_unrealized_pnl"] = unrealized
                row["fifo_pnl_unrealized"] = unrealized

    def _compute_fifo_cost_basis(self, symbols: set[str]) -> dict[str, dict]:
        """Compute FIFO cost basis for symbols from trade records.

        Delegates to the shared FIFO utility.
        """
        if not symbols:
            return {}
        placeholders = ",".join("?" for _ in symbols)
        trades = self.db.execute(
            f"""
            SELECT symbol, asset_class, trade_date, buy_sell, quantity, trade_price
            FROM trade_records
            WHERE symbol IN ({placeholders})
            ORDER BY symbol, trade_date ASC, date_time ASC
            """,
            tuple(symbols),
        )
        return compute_fifo_cost_basis(trades)

    def _enrich_realized_pnl(self, rows: list[dict], report_date: str) -> None:
        """Fill in total_realized_pnl from trade records.

        First tries SUM(fifo_pnl_realized) from DB.
        Falls back to FIFO computation when API zeroes the field.
        """
        # Check if DB has non-zero realized PnL
        check = self.db.execute_one(
            "SELECT COALESCE(SUM(fifo_pnl_realized), 0.0) AS total FROM trade_records WHERE trade_date <= ?",
            (report_date,),
        )
        has_db_data = check and abs(float(check["total"])) > 0.01

        if has_db_data:
            # Use DB values directly
            pnl_rows = self.db.execute(
                """
                SELECT symbol, COALESCE(SUM(fifo_pnl_realized), 0.0) AS realized_pnl
                FROM trade_records WHERE trade_date <= ?
                GROUP BY symbol
                """,
                (report_date,),
            )
            pnl_lookup: dict[str, float] = {r["symbol"]: float(r["realized_pnl"]) for r in pnl_rows}
            for row in rows:
                if not row.get("total_realized_pnl"):
                    row["total_realized_pnl"] = pnl_lookup.get(row.get("symbol"), 0.0)
        else:
            # Compute from FIFO
            symbols = {r["symbol"] for r in rows if r.get("symbol")}
            if not symbols:
                return
            fifo_map = self._compute_fifo_cost_basis(symbols)
            for row in rows:
                sym = row.get("symbol")
                if sym in fifo_map and not row.get("total_realized_pnl"):
                    row["total_realized_pnl"] = fifo_map[sym].get("realized_pnl", 0.0)

    @staticmethod
    def _row_to_position_item(row: dict) -> PositionItem:
        realized = float(row.get("total_realized_pnl") or 0.0)
        unrealized = float(row.get("total_unrealized_pnl") or 0.0)
        cost = row.get("cost_basis_money")
        return PositionItem(
            account_id=row["account_id"],
            report_date=row["report_date"],
            symbol=row.get("symbol"),
            description=row.get("description"),
            asset_class=row.get("asset_class"),
            quantity=row.get("quantity"),
            mark_price=row.get("mark_price"),
            position_value=row.get("position_value"),
            percent_of_nav=row.get("percent_of_nav"),
            average_cost_price=row.get("average_cost_price"),
            cost_basis_money=cost,
            total_realized_pnl=realized,
            realized_pnl_percent=(
                realized / abs(float(cost)) * 100.0 if cost and float(cost) != 0 else None
            ),
            total_unrealized_pnl=unrealized,
            unrealized_pnl_percent=(
                unrealized / abs(float(cost)) * 100.0 if cost and float(cost) != 0 else None
            ),
            total_fifo_pnl=realized + unrealized,
            previous_day_change_percent=row.get("previous_day_change_percent"),
        )

    def _build_summary(
        self,
        report_date: str,
        symbol: str | None,
        asset_class: str | None,
        page_rows: list[dict],
    ) -> PositionSummaryResponse:
        """Build summary from the full date (not just the page)."""
        return self.get_positions_summary(
            report_date=report_date,
            symbol=symbol,
            asset_class=asset_class,
        )
