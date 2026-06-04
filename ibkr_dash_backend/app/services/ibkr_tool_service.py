"""IBKR Account Tool Service for Account Copilot.

Wraps the Database to provide tool methods that the copilot can call.
Each method queries SQLite and returns a dict result.
"""

from __future__ import annotations

import json
from typing import Any

from app.core.database import Database


class IbkrToolService:
    """Provides IBKR account data tools for the Account Copilot."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def get_account_overview(self, **kwargs: Any) -> dict:
        """Get latest account overview."""
        row = self.db.execute_one(
            "SELECT * FROM account_snapshots ORDER BY report_date DESC LIMIT 1"
        )
        if not row:
            return {"error": "No account data available"}
        return {
            "account_id": row.get("account_id"),
            "report_date": row.get("report_date"),
            "total_equity": row.get("total_equity"),
            "cash": row.get("cash"),
            "stock_value": row.get("stock_value"),
            "currency": row.get("currency", "USD"),
        }

    def get_current_positions(self, **kwargs: Any) -> dict:
        """Get current positions sorted by value."""
        rows = self.db.execute(
            "SELECT symbol, description, quantity, mark_price, position_value, "
            "percent_of_nav, total_unrealized_pnl, total_realized_pnl "
            "FROM position_snapshots ORDER BY report_date DESC, position_value DESC LIMIT 50"
        )
        return {
            "positions": rows,
            "count": len(rows),
            "total_value": sum(r.get("position_value", 0) or 0 for r in rows),
        }

    def get_symbol_position(self, symbol: str = "", **kwargs: Any) -> dict:
        """Get position details for a specific symbol."""
        if not symbol:
            return {"error": "symbol is required"}
        rows = self.db.execute(
            "SELECT * FROM position_snapshots WHERE symbol LIKE ? ORDER BY report_date DESC LIMIT 10",
            (f"%{symbol}%",),
        )
        if not rows:
            return {"error": f"No position found for {symbol}"}
        return {"symbol": symbol, "positions": rows}

    def get_symbol_trades(self, symbol: str = "", **kwargs: Any) -> dict:
        """Get trade history for a specific symbol."""
        if not symbol:
            return {"error": "symbol is required"}
        rows = self.db.execute(
            "SELECT trade_date, buy_sell, quantity, trade_price, net_cash, fifo_pnl_realized "
            "FROM trade_records WHERE symbol LIKE ? ORDER BY trade_date DESC LIMIT 50",
            (f"%{symbol}%",),
        )
        return {"symbol": symbol, "trades": rows, "count": len(rows)}

    def get_position_history(self, symbol: str = "", **kwargs: Any) -> dict:
        """Get position history for a symbol."""
        if not symbol:
            return {"error": "symbol is required"}
        rows = self.db.execute(
            "SELECT report_date, quantity, mark_price, position_value "
            "FROM position_snapshots WHERE symbol LIKE ? ORDER BY report_date DESC LIMIT 100",
            (f"%{symbol}%",),
        )
        return {"symbol": symbol, "history": rows, "count": len(rows)}

    def get_equity_curve(self, **kwargs: Any) -> dict:
        """Get account equity curve."""
        rows = self.db.execute(
            "SELECT report_date, total_equity, cash, stock_value "
            "FROM account_snapshots ORDER BY report_date ASC LIMIT 500"
        )
        return {"curve": rows, "count": len(rows)}

    def get_daily_attribution(self, report_date: str = "", **kwargs: Any) -> dict:
        """Get daily P&L attribution."""
        if report_date:
            rows = self.db.execute(
                "SELECT symbol, total_unrealized_pnl, total_realized_pnl, percent_of_nav "
                "FROM position_snapshots WHERE report_date = ? ORDER BY total_unrealized_pnl ASC LIMIT 20",
                (report_date,),
            )
        else:
            rows = self.db.execute(
                "SELECT symbol, total_unrealized_pnl, total_realized_pnl, percent_of_nav "
                "FROM position_snapshots ORDER BY report_date DESC, total_unrealized_pnl ASC LIMIT 20"
            )
        return {"attribution": rows, "count": len(rows)}

    def get_risk_snapshot(self, **kwargs: Any) -> dict:
        """Get portfolio risk snapshot."""
        positions = self.db.execute(
            "SELECT symbol, position_value, percent_of_nav "
            "FROM position_snapshots ORDER BY position_value DESC LIMIT 50"
        )
        total_value = sum(p.get("position_value", 0) or 0 for p in positions)
        top_3_pct = sum(p.get("percent_of_nav", 0) or 0 for p in positions[:3])
        return {
            "total_positions": len(positions),
            "total_value": total_value,
            "top_3_concentration_pct": round(top_3_pct, 2),
            "positions": positions[:10],
        }

    def get_cash_flow_summary(self, **kwargs: Any) -> dict:
        """Get cash flow summary."""
        rows = self.db.execute(
            "SELECT flow_type, SUM(amount) as total_amount, COUNT(*) as count "
            "FROM cash_flows GROUP BY flow_type ORDER BY total_amount DESC"
        )
        return {"cash_flows": rows, "count": len(rows)}
