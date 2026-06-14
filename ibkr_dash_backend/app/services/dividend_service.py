"""Dividend service: list dividend-related cash flows from SQLite.

Filters the cash_flows table to dividend and withholding-tax flow types.
"""

from __future__ import annotations

from app.core.database import Database
from app.schemas.dividends import DividendItem, DividendCurrencySummaryItem, DividendListResponse, DividendSummaryResponse
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
    """Service for querying and filtering dividend records."""

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

    def get_summary(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        currency: str | None = None,
        symbol: str | None = None,
    ) -> DividendSummaryResponse:
        """Return aggregated dividend summary."""
        effective_start = parse_date(start_date)
        effective_end = parse_date(end_date)

        conditions = ["flow_type IN ({})".format(",".join("?" for _ in DIVIDEND_FLOW_TYPES))]
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

        # Dividend and tax subtotals
        dividend_types_str = ",".join("?" for _ in DIVIDEND_FLOW_TYPES)
        tax_types = ("Withholding Tax",)
        tax_types_str = ",".join("?" for _ in tax_types)

        row = self.db.execute_one(
            f"""
            SELECT
                COUNT(*) AS record_count,
                SUM(CASE WHEN flow_type != 'Withholding Tax' THEN 1 ELSE 0 END) AS dividend_count,
                SUM(CASE WHEN flow_type = 'Withholding Tax' THEN 1 ELSE 0 END) AS tax_count,
                COALESCE(SUM(CASE WHEN flow_type != 'Withholding Tax' THEN amount_in_base ELSE 0 END), 0) AS gross_div,
                COALESCE(SUM(CASE WHEN flow_type = 'Withholding Tax' THEN amount_in_base ELSE 0 END), 0) AS tax_amt,
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
                SUM(CASE WHEN flow_type != 'Withholding Tax' THEN 1 ELSE 0 END) AS dividend_count,
                SUM(CASE WHEN flow_type = 'Withholding Tax' THEN 1 ELSE 0 END) AS tax_count,
                COALESCE(SUM(CASE WHEN flow_type != 'Withholding Tax' THEN amount_in_base ELSE 0 END), 0) AS gross_div,
                COALESCE(SUM(CASE WHEN flow_type = 'Withholding Tax' THEN amount_in_base ELSE 0 END), 0) AS tax_amt,
                COALESCE(SUM(amount_in_base), 0) AS net_amount
            FROM cash_flows
            WHERE {where_clause}
            GROUP BY currency
            ORDER BY SUM(amount_in_base) DESC
            """,
            tuple(params),
        )

        by_currency = [
            DividendCurrencySummaryItem(
                currency=r["currency"],
                record_count=int(r["record_count"] or 0),
                dividend_count=int(r["dividend_count"] or 0),
                withholding_tax_count=int(r["tax_count"] or 0),
                gross_dividend_amount=float(r["gross_div"] or 0),
                withholding_tax_amount=float(r["tax_amt"] or 0),
                net_amount=float(r["net_amount"] or 0),
            )
            for r in currency_rows
        ]

        return DividendSummaryResponse(
            record_count=int(row["record_count"] or 0) if row else 0,
            dividend_count=int(row["dividend_count"] or 0) if row else 0,
            withholding_tax_count=int(row["tax_count"] or 0) if row else 0,
            gross_dividend_amount=float(row["gross_div"] or 0) if row else None,
            withholding_tax_amount=float(row["tax_amt"] or 0) if row else None,
            net_amount=float(row["net_amount"] or 0) if row else None,
            by_currency=by_currency,
        )
