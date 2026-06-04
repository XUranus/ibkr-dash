"""Cash flow service: list cash flows from SQLite.

Filters to deposits/withdrawals flow types by default.
"""

from __future__ import annotations

from app.core.database import Database
from app.schemas.cash_flows import CashFlowItem, CashFlowListResponse
from app.utils.dates import parse_date
from app.utils.pagination import build_pagination, build_pagination_info

CASH_FLOW_SORT_FIELDS = {
    "date_time",
    "settle_date",
    "amount",
    "currency",
}

# Only show deposit/withdrawal flows by default
DEPOSIT_WITHDRAWAL_TYPES = ("Deposits/Withdrawals",)


class CashFlowService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list_cash_flows(
        self,
        start_date: str | None,
        end_date: str | None,
        currency: str | None,
        flow_direction: str | None,
        sort_by: str,
        sort_order: str,
        page: int,
        page_size: int,
    ) -> CashFlowListResponse:
        """List deposit/withdrawal cash flows with filtering and pagination."""
        effective_start = parse_date(start_date)
        effective_end = parse_date(end_date)

        conditions = ["cf.flow_type IN ({})".format(",".join("?" for _ in DEPOSIT_WITHDRAWAL_TYPES))]
        params: list = list(DEPOSIT_WITHDRAWAL_TYPES)

        if effective_start:
            conditions.append("cf.date_time >= ?")
            params.append(effective_start.isoformat())
        if effective_end:
            conditions.append("cf.date_time <= ?")
            params.append(effective_end.isoformat())
        if currency:
            conditions.append("cf.currency = ?")
            params.append(currency)

        # flow_direction is inferred from amount sign
        where_clause = " AND ".join(conditions)
        safe_sort_by = sort_by if sort_by in CASH_FLOW_SORT_FIELDS else "date_time"
        safe_sort_order = "ASC" if sort_order.lower() == "asc" else "DESC"

        count_row = self.db.execute_one(
            f"SELECT COUNT(*) AS cnt FROM cash_flows cf WHERE {where_clause}",
            tuple(params),
        )
        total = int(count_row["cnt"]) if count_row else 0

        offset, limit = build_pagination(page, page_size)
        rows = self.db.execute(
            f"""
            SELECT cf.account_id, cf.currency, cf.symbol, cf.description,
                   cf.date_time, cf.settle_date, cf.amount, cf.amount_in_base,
                   cf.flow_type, cf.dividend_type, cf.transaction_id
            FROM cash_flows cf
            WHERE {where_clause}
            ORDER BY cf.{safe_sort_by} {safe_sort_order} NULLS LAST
            LIMIT ? OFFSET ?
            """,
            tuple(params) + (limit, offset),
        )

        items = [CashFlowItem(**row) for row in rows]
        return CashFlowListResponse(
            items=items,
            pagination=build_pagination_info(page, limit, total),
        )
