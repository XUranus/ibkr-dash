"""FIFO cost basis computation from trade records.

Computes cost basis, average cost, and realized PnL using
First-In-First-Out accounting for both long and short positions.
Handles options (1 contract = 100 shares) automatically.
"""

from __future__ import annotations

import hashlib
import json
import time

# Module-level cache for FIFO results (keyed by sorted symbols + report_date)
_fifo_cache: dict[str, tuple[float, dict]] = {}
_fifo_cache_ttl: float = 86400.0  # 24 hours

OPTION_MULTIPLIER = 100  # 1 options contract = 100 shares

# Trade side constants
_BUY_SIDES = {"BUY", "B"}
_SELL_SIDES = {"SELL", "SS", "SL"}


def compute_fifo_cost_basis(trades: list[dict]) -> dict[str, dict]:
    """Compute FIFO cost basis for a set of trades.

    Args:
        trades: List of trade dicts with keys:
            symbol, asset_class, trade_date, buy_sell, quantity, trade_price

    Returns:
        Dict mapping symbol to {
            cost_basis: float,      # total cost of open positions
            avg_cost: float,        # average cost per share
            total_qty: float,       # signed total quantity (+ long, - short)
            realized_pnl: float     # cumulative realized PnL
        }
    """
    # Group trades by symbol
    trades_by_symbol: dict[str, list[dict]] = {}
    for t in trades:
        sym = t.get("symbol")
        if sym:
            trades_by_symbol.setdefault(sym, []).append(t)

    result: dict[str, dict] = {}
    for sym, sym_trades in trades_by_symbol.items():
        # Deduplicate (XML parser may create duplicates across FlexStatements)
        seen: set[str] = set()
        unique: list[dict] = []
        for t in sym_trades:
            key = f"{t.get('trade_date')}:{t.get('buy_sell')}:{t.get('quantity')}:{t.get('trade_price')}"
            if key not in seen:
                seen.add(key)
                unique.append(t)

        # FIFO tracking: list of (signed_quantity, price)
        # Positive = long, negative = short
        open_positions: list[tuple[float, float]] = []
        realized_pnl = 0.0

        for t in unique:
            buy_sell = (t.get("buy_sell") or "").upper()
            raw_qty = float(t.get("quantity") or 0)
            price = float(t.get("trade_price") or 0)

            # Options: IBKR reports quantity in contracts (1 = 100 shares)
            if (t.get("asset_class") or "") == "OPT":
                raw_qty = raw_qty * OPTION_MULTIPLIER

            if raw_qty == 0 or price <= 0:
                continue

            # BUY = positive, SELL = negative
            trade_qty = raw_qty if buy_sell in _BUY_SIDES else -abs(raw_qty)

            # Close existing positions with opposite sign first (FIFO)
            remaining = trade_qty
            while remaining != 0 and open_positions:
                oq, op = open_positions[0]
                # Same sign → can't close, break
                if (remaining > 0 and oq > 0) or (remaining < 0 and oq < 0):
                    break
                # Opposite sign → close
                close_qty = min(abs(remaining), abs(oq))
                if oq > 0:  # closing long
                    realized_pnl += close_qty * (price - op)
                else:  # closing short
                    realized_pnl += close_qty * (op - price)
                # Reduce remaining
                if remaining > 0:
                    remaining -= close_qty
                else:
                    remaining += close_qty
                if abs(close_qty) >= abs(oq):
                    open_positions.pop(0)
                else:
                    # Partially close: reduce the open position
                    if oq > 0:
                        open_positions[0] = (oq - close_qty, op)
                    else:
                        open_positions[0] = (oq + close_qty, op)
                    break

            # Open new position with remaining quantity
            # For stocks (non-OPTION): only allow long positions
            # For options: allow both long and short
            is_option = (t.get("asset_class") or "").upper() == "OPT"
            if abs(remaining) > 0.001 and (is_option or remaining > 0):
                open_positions.append((remaining, price))

        # Compute cost basis from remaining open positions
        total_cost = sum(abs(q) * p for q, p in open_positions)
        total_qty = sum(q for q, _ in open_positions)

        if total_cost > 0:
            result[sym] = {
                "cost_basis": total_cost,
                "avg_cost": total_cost / abs(total_qty) if total_qty != 0 else 0,
                "total_qty": total_qty,
                "realized_pnl": realized_pnl,
            }

    return result


def query_fifo_cost_basis(
    db,
    symbols: set[str],
    report_date: str | None = None,
) -> dict[str, dict]:
    """Query trades from DB and compute FIFO cost basis.

    Results are cached in-memory for 24 hours since trade data
    only changes on import.

    Args:
        db: Database instance.
        symbols: Set of symbols to compute FIFO for.
        report_date: If provided, only include trades up to this date.

    Returns:
        Dict mapping symbol to {cost_basis, avg_cost, total_qty, realized_pnl}.
    """
    if not symbols:
        return {}

    # Check cache
    cache_raw = json.dumps([sorted(symbols), report_date or ""], sort_keys=True)
    cache_key = hashlib.md5(cache_raw.encode()).hexdigest()[:16]
    cached_entry = _fifo_cache.get(cache_key)
    if cached_entry is not None:
        expires_at, cached_value = cached_entry
        if time.time() <= expires_at:
            return cached_value
        del _fifo_cache[cache_key]

    placeholders = ",".join("?" for _ in symbols)
    if report_date:
        trades = db.execute(
            f"""
            SELECT symbol, asset_class, trade_date, buy_sell, quantity, trade_price
            FROM trade_records
            WHERE symbol IN ({placeholders}) AND trade_date <= ?
            ORDER BY symbol, trade_date ASC, date_time ASC
            """,
            tuple(symbols) + (report_date,),
        )
    else:
        trades = db.execute(
            f"""
            SELECT symbol, asset_class, trade_date, buy_sell, quantity, trade_price
            FROM trade_records
            WHERE symbol IN ({placeholders})
            ORDER BY symbol, trade_date ASC, date_time ASC
            """,
            tuple(symbols),
        )
    result = compute_fifo_cost_basis(trades)
    _fifo_cache[cache_key] = (time.time() + _fifo_cache_ttl, result)
    return result


def invalidate_fifo_cache() -> int:
    """Clear the FIFO cost basis cache. Called after data import."""
    global _fifo_cache
    count = len(_fifo_cache)
    _fifo_cache = {}
    return count
