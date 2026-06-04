"""Dividend service: list dividend-related cash flows from SQLite.

Filters the cash_flows table to dividend and withholding-tax flow types.
"""

from __future__ import annotations

from app.core.database import Database
from app.schemas.dividends import DividendItem, DividendListResponse
from app.utils.dates import parse_date
from app.utils.pagination import build_pagination, build_pagination_info

DIVIDEND_FLOW_TYPES = (
    "Dividends",
    "Ordinary Dividend",
    "Withholding Tax",
    "Payment In Lieu Of Dividends",
    "Payment In Lieu Of Dividend",
)

DIVIDEND_SORT_FIELDS = {
    "date_time",
    "amount",
    "symbol",
}


class DividendService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list_dividends(
        self,
        start_date: str | None,
        end_date: str | None,
        currency: str | None,
        symbol: str | None,
        sort_by: str,
        sort_order: str,
        page: int,
        page_size: int,
    ) -> DividendListResponse:
        """List dividend cash flows with filtering and pagination."""
        effective_start = parse_date(start_date)
        effective_end = parse_date(end_date)

        conditions = [
            "flow_type IN ({})".format(",".join("?" for _ in DIVIDEND_FLOW_TYPES))
        ]
        params: list = list(DIVIDEND_FLOW_TYPES)

        if effective_start:
            conditions.append("date_time >= ?")
            params.append(effective_start.isoformat())
        if effective_end:
            conditions.append("date_time <= ?")
            params.append(effective_end.isoformat())
        if currency:
            conditions.append("UPPER(currency) = ?")
            params.append(currency.upper())
        if symbol:
            conditions.append("UPPER(symbol) = ?")
            params.append(symbol.upper())

        where_clause = " AND ".join(conditions)
        safe_sort_by = sort_by if sort_by in DIVIDEND_SORT_FIELDS else "date_time"
        safe_sort_order = "ASC" if sort_order.lower() == "asc" else "DESC"

        count_row = self.db.execute_one(
            f"SELECT COUNT(*) AS cnt FROM cash_flows WHERE {where_clause}",
            tuple(params),
        )
        total = int(count_row["cnt"]) if count_row else 0

        offset, limit = build_pagination(page, page_size)
        rows = self.db.execute(
            f"""
            SELECT account_id, currency, symbol, description,
                   date_time, settle_date, amount, flow_type,
                   dividend_type, transaction_id
            FROM cash_flows
            WHERE {where_clause}
            ORDER BY {safe_sort_by} {safe_sort_order} NULLS LAST
            LIMIT ? OFFSET ?
            """,
            tuple(params) + (limit, offset),
        )

        items = [DividendItem(**row) for row in rows]
        return DividendListResponse(
            items=items,
            pagination=build_pagination_info(page, limit, total),
        )
