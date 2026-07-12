"""Symbol analysis service -- financial analysis for individual symbols.

Combines Longbridge financial data with local portfolio data to provide
comprehensive symbol analysis.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.database import Database
from app.services.longbridge_service import LongbridgeService, LongbridgeUnavailableError, LongbridgeExternalDataError

logger = logging.getLogger(__name__)


class SymbolAnalysisService:
    """Symbol financial analysis combining external and internal data."""

    def __init__(self, db: Database, longbridge: LongbridgeService) -> None:
        self.db = db
        self.longbridge = longbridge

    async def get_financials(self, symbol: str, periods: int = 8, report: str = "qf") -> dict[str, Any]:
        """Get financial statements for a symbol from Longbridge."""
        try:
            return await self.longbridge.get_financials(symbol, periods, report)
        except LongbridgeUnavailableError:
            raise
        except LongbridgeExternalDataError:
            raise
        except Exception as exc:
            logger.warning("Failed to get financials for %s: %s", symbol, exc)
            raise LongbridgeExternalDataError(str(exc)) from exc

    async def compare(self, left_symbol: str, right_symbol: str, periods: int = 8, report: str = "qf") -> dict[str, Any]:
        """Compare financials of two symbols."""
        left = await self.get_financials(left_symbol, periods, report)
        right = await self.get_financials(right_symbol, periods, report)
        return {
            "left": {"symbol": left_symbol, "financials": left},
            "right": {"symbol": right_symbol, "financials": right},
        }

    def get_portfolio_context(self, symbol: str) -> dict[str, Any]:
        """Get portfolio context for a symbol from local data."""
        # Get latest position
        position = self.db.execute_one(
            "SELECT * FROM position_snapshots WHERE symbol = ? ORDER BY report_date DESC LIMIT 1",
            (symbol,),
        )
        # Get recent trades
        trades = self.db.execute(
            "SELECT * FROM trade_records WHERE symbol = ? ORDER BY trade_date DESC LIMIT 10",
            (symbol,),
        )
        # Get price history
        prices = self.db.execute(
            "SELECT * FROM price_history WHERE symbol = ? ORDER BY report_date DESC LIMIT 30",
            (symbol,),
        )
        return {
            "position": position,
            "recent_trades": trades,
            "price_history": prices,
        }
