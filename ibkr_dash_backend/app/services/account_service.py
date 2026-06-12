"""Account overview and snapshot service.

Queries the account_snapshots table for the latest snapshot and computes
day-over-day deltas by comparing with the previous snapshot.
"""

from __future__ import annotations

from app.core.database import Database
from app.schemas.account import (
    AccountDeltaMetric,
    AccountOverviewResponse,
    AccountSnapshot,
    AccountSnapshotListResponse,
)


class AccountService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_overview(self) -> AccountOverviewResponse | None:
        """Return the latest account overview with deltas vs. previous day."""
        snapshots = self.db.execute(
            """
            SELECT * FROM account_snapshots
            ORDER BY report_date DESC
            LIMIT 2
            """
        )
        if not snapshots:
            return None

        current = snapshots[0]
        previous = snapshots[1] if len(snapshots) > 1 else None

        # Compute aggregate PnL from trade and position tables
        realized_pnl = self._compute_realized_pnl(current["report_date"])
        unrealized_pnl = self._compute_unrealized_pnl(current["report_date"])
        total_pnl = realized_pnl + unrealized_pnl

        # Compute cash from DB if stored value is 0
        cash = current.get("cash") or 0
        if cash == 0:
            total_equity = current.get("total_equity") or 0
            pos_row = self.db.execute_one(
                "SELECT COALESCE(SUM(position_value), 0.0) AS total FROM position_snapshots WHERE report_date = ?",
                (current["report_date"],),
            )
            pos_total = float(pos_row["total"]) if pos_row else 0
            if total_equity > 0 and pos_total > 0:
                cash = max(total_equity - pos_total, 0)

        overview = AccountOverviewResponse(
            account_id=current["account_id"],
            report_date=current["report_date"],
            currency=current.get("currency"),
            total_equity=current.get("total_equity"),
            cash=cash,
            stock_value=current.get("stock_value") or (total_equity - cash if total_equity else 0),
            options_value=current.get("options_value"),
            funds_value=current.get("funds_value"),
            crypto_value=current.get("crypto_value"),
            fifo_total_realized_pnl=realized_pnl,
            fifo_total_unrealized_pnl=unrealized_pnl,
            fifo_total_pnl=total_pnl,
            cnav_mtm=current.get("cnav_mtm"),
            cnav_twr=current.get("cnav_twr"),
        )

        if previous is not None:
            overview.total_equity_delta = self._build_delta(
                current.get("total_equity"), previous.get("total_equity")
            )

            prev_realized = self._compute_realized_pnl(previous["report_date"])
            prev_unrealized = self._compute_unrealized_pnl(previous["report_date"])
            prev_total = prev_realized + prev_unrealized

            overview.fifo_total_realized_pnl_delta = self._build_delta(realized_pnl, prev_realized)
            overview.fifo_total_unrealized_pnl_delta = self._build_delta(unrealized_pnl, prev_unrealized)
            overview.fifo_total_pnl_delta = self._build_delta(total_pnl, prev_total)

        return overview

    def get_snapshots(self, limit: int = 30) -> AccountSnapshotListResponse:
        """Return recent account snapshots ordered by date descending."""
        rows = self.db.execute(
            """
            SELECT account_id, report_date, currency, total_equity, cash,
                   stock_value, options_value, funds_value, crypto_value,
                   cnav_mtm, cnav_twr, fifo_total_realized_pnl,
                   fifo_total_unrealized_pnl
            FROM account_snapshots
            ORDER BY report_date DESC
            LIMIT ?
            """,
            (limit,),
        )
        items = [AccountSnapshot(**row) for row in rows]
        return AccountSnapshotListResponse(items=items)

    def _compute_realized_pnl(self, report_date: str) -> float:
        """Sum realized PnL from trades up to the given date."""
        row = self.db.execute_one(
            """
            SELECT COALESCE(SUM(fifo_pnl_realized), 0.0) AS total
            FROM trade_records
            WHERE trade_date <= ?
            """,
            (report_date,),
        )
        return float(row["total"]) if row else 0.0

    def _compute_unrealized_pnl(self, report_date: str) -> float:
        """Compute unrealized PnL from position snapshots.

        Uses position_value - (quantity * average_cost_price) for each position.
        Falls back to cumulative MTM if cost basis is not available.
        """
        # Try to compute from position data
        rows = self.db.execute(
            "SELECT COALESCE(SUM(total_unrealized_pnl), 0.0) AS total FROM position_snapshots WHERE report_date = ?",
            (report_date,),
        )
        total = float(rows[0]["total"]) if rows else 0.0
        if total != 0:
            return total

        # Fallback: cumulative MTM from account snapshots
        rows = self.db.execute(
            "SELECT COALESCE(SUM(cnav_mtm), 0.0) AS cumulative_mtm FROM account_snapshots WHERE report_date <= ?",
            (report_date,),
        )
        return float(rows[0]["cumulative_mtm"]) if rows else 0.0

    @staticmethod
    def _build_delta(current: float | None, previous: float | None) -> AccountDeltaMetric | None:
        """Compute the day-over-day change metric."""
        if current is None or previous is None:
            return None
        amount_change = float(current) - float(previous)
        percent_change = None
        if float(previous) != 0.0:
            percent_change = amount_change / abs(float(previous)) * 100.0
        return AccountDeltaMetric(amount_change=amount_change, percent_change=percent_change)
