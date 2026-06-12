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

        # Compute net cost from TWR-based cumulative PnL
        net_cost = self._compute_net_cost(current["report_date"], total_equity, cash)

        # total_pnl = equity - net_cost
        total_pnl = total_equity - net_cost if net_cost > 0 else 0.0

        # Get unrealized PnL from position data (ibkr-show-public approach)
        unrealized_pnl = self._compute_unrealized_from_positions(current["report_date"])

        # Derive realized PnL: realized = total_pnl - unrealized
        # This is more accurate than SUM(fifo_pnl_realized) from trades,
        # because the real-time API zeroes out fifo_pnl_realized.
        realized_pnl = total_pnl - unrealized_pnl

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
            prev_total_pnl = prev_equity - prev_net_cost if prev_net_cost > 0 else 0.0
            prev_unrealized = self._compute_unrealized_from_positions(previous["report_date"])
            prev_realized = prev_total_pnl - prev_unrealized

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

    def _compute_unrealized_from_positions(self, report_date: str) -> float:
        """Compute unrealized PnL from position snapshots.

        Uses SUM(fifo_pnl_unrealized) when available.
        Falls back to SUM(position_value - cost_basis_money) when unrealized is 0.
        Falls back to computing cost basis from trades via FIFO.
        """
        # Try the given date
        row = self.db.execute_one(
            "SELECT COALESCE(SUM(fifo_pnl_unrealized), 0.0) AS total FROM position_snapshots WHERE report_date = ?",
            (report_date,),
        )
        val = float(row["total"]) if row else 0.0
        if val != 0:
            return val

        # Fallback: compute from position_value - cost_basis_money
        row = self.db.execute_one(
            """
            SELECT COALESCE(SUM(position_value - cost_basis_money), 0.0) AS total
            FROM position_snapshots
            WHERE report_date = ? AND cost_basis_money > 0
            """,
            (report_date,),
        )
        val = float(row["total"]) if row else 0.0
        if val != 0:
            return val

        # Fallback: compute cost basis from trades via FIFO
        positions = self.db.execute(
            "SELECT symbol, quantity, position_value FROM position_snapshots WHERE report_date = ?",
            (report_date,),
        )
        if not positions:
            return 0.0

        symbols = {p["symbol"] for p in positions if p.get("symbol")}
        if not symbols:
            return 0.0

        fifo_map = self._compute_fifo_cost_basis(symbols)
        total_unrealized = 0.0
        for p in positions:
            sym = p.get("symbol")
            qty = float(p.get("quantity") or 0)
            value = float(p.get("position_value") or 0)
            if sym in fifo_map:
                fifo_cost = fifo_map[sym]["cost_basis"]
                fifo_qty = fifo_map[sym]["total_qty"]
                if fifo_qty > 0 and qty > 0 and abs(fifo_qty - qty) > 0.01:
                    cost = fifo_cost * (qty / fifo_qty)
                else:
                    cost = fifo_cost
                total_unrealized += value - cost
        return total_unrealized

    def _compute_fifo_cost_basis(self, symbols: set[str]) -> dict[str, dict]:
        """Compute FIFO cost basis for symbols from trade records."""
        if not symbols:
            return {}
        placeholders = ",".join("?" for _ in symbols)
        trades = self.db.execute(
            f"""
            SELECT symbol, trade_date, buy_sell, quantity, trade_price
            FROM trade_records
            WHERE symbol IN ({placeholders})
            ORDER BY symbol, trade_date ASC, date_time ASC
            """,
            tuple(symbols),
        )

        trades_by_symbol: dict[str, list[dict]] = {}
        for t in trades:
            trades_by_symbol.setdefault(t["symbol"], []).append(t)

        result: dict[str, dict] = {}
        for sym, sym_trades in trades_by_symbol.items():
            seen: set[str] = set()
            unique: list[dict] = []
            for t in sym_trades:
                key = f"{t['trade_date']}:{t['buy_sell']}:{t['quantity']}:{t['trade_price']}"
                if key not in seen:
                    seen.add(key)
                    unique.append(t)

            open_pos: list[tuple[float, float]] = []
            for t in unique:
                buy_sell = (t.get("buy_sell") or "").upper()
                qty = abs(float(t.get("quantity") or 0))
                price = float(t.get("trade_price") or 0)
                if qty <= 0 or price <= 0:
                    continue
                if buy_sell in ("BUY", "B"):
                    open_pos.append((qty, price))
                elif buy_sell in ("SELL", "SS", "SL"):
                    remaining = qty
                    while remaining > 0 and open_pos:
                        oq, op = open_pos[0]
                        closed = min(remaining, oq)
                        remaining -= closed
                        if closed >= oq:
                            open_pos.pop(0)
                        else:
                            open_pos[0] = (oq - closed, op)

            total_cost = sum(q * p for q, p in open_pos)
            total_qty = sum(q for q, _ in open_pos)
            if total_cost > 0:
                result[sym] = {"cost_basis": total_cost, "total_qty": total_qty}

        return result

    def _compute_net_cost(self, report_date: str, total_equity: float, _cash: float) -> float:
        """Compute net cost (total investment) using TWR-based cumulative PnL.

        net_cost = total_equity - cumulative_market_pnl
        where cumulative_market_pnl = Σ(daily_twr * prev_equity / 100) for all days up to report_date.

        This correctly handles deposits: when a deposit arrives, total_equity rises
        but cumulative_market_pnl doesn't (TWR excludes cash flows), so net_cost increases.
        """
        rows = self.db.execute(
            """
            SELECT total_equity, cnav_twr, cnav_mtm, cnav_deposits,
                   cnav_change_in_unrealized, cnav_realized
            FROM account_snapshots
            WHERE report_date <= ?
            ORDER BY report_date ASC
            """,
            (report_date,),
        )
        if not rows:
            return 0.0

        cumulative_pnl = 0.0
        prev_equity = None
        for row in rows:
            equity = row.get("total_equity")
            twr = row.get("cnav_twr")
            cumtm = row.get("cnav_mtm")
            deposits = row.get("cnav_deposits") or 0.0
            chg_unreal = row.get("cnav_change_in_unrealized")
            rlsd = row.get("cnav_realized")

            # Compute daily PnL (same logic as chart_service)
            detail_pnl = (float(chg_unreal or 0) + float(rlsd or 0))
            detail_ok = (
                chg_unreal is not None and rlsd is not None
                and not (detail_pnl == 0.0 and twr is not None and float(twr or 0) != 0.0)
            )
            if detail_ok:
                cumulative_pnl += detail_pnl
            elif twr is not None and prev_equity is not None and prev_equity != 0:
                cumulative_pnl += float(prev_equity) * float(twr) / 100.0
            elif cumtm is not None:
                cumulative_pnl += float(cumtm) - float(deposits)

            prev_equity = float(equity) if equity is not None else prev_equity

        net_cost = float(total_equity) - cumulative_pnl
        return max(net_cost, 0.0)

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
