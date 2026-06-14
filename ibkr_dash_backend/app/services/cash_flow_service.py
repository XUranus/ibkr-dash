"""Cash flow service: list cash flows from SQLite.

Filters to deposits/withdrawals flow types by default.
"""

from __future__ import annotations

from app.core.database import Database
from app.schemas.cash_flows import CashFlowItem, CashFlowCurrencySummaryItem, CashFlowListResponse, CashFlowSummaryResponse
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
    """Service for querying and filtering cash flow records."""

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

    def get_summary(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        currency: str | None = None,
    ) -> CashFlowSummaryResponse:
        """Return aggregated cash flow summary."""
        effective_start = parse_date(start_date)
        effective_end = parse_date(end_date)

        conditions = ["flow_type IN ({})".format(",".join("?" for _ in DEPOSIT_WITHDRAWAL_TYPES))]
        params: list = list(DEPOSIT_WITHDRAWAL_TYPES)

        if effective_start:
            conditions.append("date_time >= ?")
            params.append(effective_start.isoformat())
        if effective_end:
            conditions.append("date_time <= ?")
            params.append(effective_end.isoformat())
        if currency:
            conditions.append("currency = ?")
            params.append(currency)

        where_clause = " AND ".join(conditions)

        # Overall summary
        row = self.db.execute_one(
            f"""
            SELECT
                COUNT(*) AS record_count,
                SUM(CASE WHEN amount_in_base > 0 THEN 1 ELSE 0 END) AS deposit_count,
                SUM(CASE WHEN amount_in_base < 0 THEN 1 ELSE 0 END) AS withdrawal_count,
                COALESCE(SUM(CASE WHEN amount_in_base > 0 THEN amount_in_base ELSE 0 END), 0) AS total_deposit,
                COALESCE(SUM(CASE WHEN amount_in_base < 0 THEN amount_in_base ELSE 0 END), 0) AS total_withdrawal,
                COALESCE(SUM(amount_in_base), 0) AS net_amount
            FROM cash_flows
            WHERE {where_clause}
            """,
            tuple(params),
        )

        # Per-currency breakdown
        currency_rows = self.db.execute(
            f"""
            SELECT
                currency,
                COUNT(*) AS record_count,
                SUM(CASE WHEN amount_in_base > 0 THEN 1 ELSE 0 END) AS deposit_count,
                SUM(CASE WHEN amount_in_base < 0 THEN 1 ELSE 0 END) AS withdrawal_count,
                COALESCE(SUM(CASE WHEN amount_in_base > 0 THEN amount_in_base ELSE 0 END), 0) AS total_deposit,
                COALESCE(SUM(CASE WHEN amount_in_base < 0 THEN amount_in_base ELSE 0 END), 0) AS total_withdrawal,
                COALESCE(SUM(amount_in_base), 0) AS net_amount
            FROM cash_flows
            WHERE {where_clause}
            GROUP BY currency
            ORDER BY SUM(amount_in_base) DESC
            """,
            tuple(params),
        )

        by_currency = [
            CashFlowCurrencySummaryItem(
                currency=r["currency"],
                record_count=int(r["record_count"] or 0),
                deposit_count=int(r["deposit_count"] or 0),
                withdrawal_count=int(r["withdrawal_count"] or 0),
                total_deposit_amount=float(r["total_deposit"] or 0),
                total_withdrawal_amount=float(r["total_withdrawal"] or 0),
                net_amount=float(r["net_amount"] or 0),
            )
            for r in currency_rows
        ]

        return CashFlowSummaryResponse(
            record_count=int(row["record_count"] or 0) if row else 0,
            deposit_count=int(row["deposit_count"] or 0) if row else 0,
            withdrawal_count=int(row["withdrawal_count"] or 0) if row else 0,
            total_deposit_amount=float(row["total_deposit"] or 0) if row else None,
            total_withdrawal_amount=float(row["total_withdrawal"] or 0) if row else None,
            net_amount=float(row["net_amount"] or 0) if row else None,
            by_currency=by_currency,
        )
