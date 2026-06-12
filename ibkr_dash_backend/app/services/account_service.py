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
        total_equity = float(current.get("total_equity") or 0)

        # Compute cash from DB if stored value is 0
        cash = current.get("cash") or 0
        if cash == 0:
            pos_row = self.db.execute_one(
                "SELECT COALESCE(SUM(position_value), 0.0) AS total FROM position_snapshots WHERE report_date = ?",
                (current["report_date"],),
            )
            pos_total = float(pos_row["total"]) if pos_row else 0
            if total_equity > 0 and pos_total > 0:
                cash = max(total_equity - pos_total, 0)

        # Compute net cost from position cost basis + cash
        net_cost = self._compute_net_cost(current["report_date"], total_equity, cash)

        # Compute realized PnL from trades
        realized_pnl = self._compute_realized_pnl(current["report_date"])

        # Derive total PnL and unrealized PnL consistently:
        # total_pnl = total_equity - net_cost
        # unrealized_pnl = total_pnl - realized_pnl
        total_pnl = total_equity - net_cost if net_cost > 0 else 0.0
        unrealized_pnl = total_pnl - realized_pnl

        overview = AccountOverviewResponse(
            account_id=current["account_id"],
            report_date=current["report_date"],
            currency=current.get("currency"),
            total_equity=total_equity,
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
            prev_equity = float(previous.get("total_equity") or 0)
            overview.total_equity_delta = self._build_delta(total_equity, prev_equity)

            prev_cash = previous.get("cash") or 0
            if prev_cash == 0:
                prev_pos = self.db.execute_one(
                    "SELECT COALESCE(SUM(position_value), 0.0) AS total FROM position_snapshots WHERE report_date = ?",
                    (previous["report_date"],),
                )
                prev_pos_total = float(prev_pos["total"]) if prev_pos else 0
                if prev_equity > 0 and prev_pos_total > 0:
                    prev_cash = max(prev_equity - prev_pos_total, 0)

            prev_net_cost = self._compute_net_cost(previous["report_date"], prev_equity, prev_cash)
            prev_realized = self._compute_realized_pnl(previous["report_date"])
            prev_total_pnl = prev_equity - prev_net_cost if prev_net_cost > 0 else 0.0
            prev_unrealized = prev_total_pnl - prev_realized

            overview.fifo_total_realized_pnl_delta = self._build_delta(realized_pnl, prev_realized)
            overview.fifo_total_unrealized_pnl_delta = self._build_delta(unrealized_pnl, prev_unrealized)
            overview.fifo_total_pnl_delta = self._build_delta(total_pnl, prev_total_pnl)

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

    def _compute_net_cost(self, report_date: str, total_equity: float, cash: float) -> float:
        """Compute net cost (total investment) from position cost basis + cash.

        Falls back to earliest cnav_starting_value if no cost basis data.
        """
        # Try position cost basis for the given date
        row = self.db.execute_one(
            "SELECT COALESCE(SUM(cost_basis_money), 0.0) AS total FROM position_snapshots WHERE report_date = ?",
            (report_date,),
        )
        cost_basis = float(row["total"]) if row else 0.0
        if cost_basis > 0:
            return cost_basis + cash

        # Fallback: use latest available cost basis
        row = self.db.execute_one(
            """
            SELECT COALESCE(SUM(cost_basis_money), 0.0) AS total
            FROM position_snapshots
            WHERE cost_basis_money > 0
            GROUP BY report_date
            ORDER BY report_date DESC LIMIT 1
            """,
        )
        if row and float(row["total"]) > 0:
            return float(row["total"]) + cash

        # Fallback: earliest cnav_starting_value
        row = self.db.execute_one(
            "SELECT cnav_starting_value FROM account_snapshots WHERE cnav_starting_value > 0 ORDER BY report_date ASC LIMIT 1"
        )
        if row and row.get("cnav_starting_value"):
            return float(row["cnav_starting_value"])

        return 0.0

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
