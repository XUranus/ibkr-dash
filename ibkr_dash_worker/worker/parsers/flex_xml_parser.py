"""Parse IBKR Flex Web Service XML responses into SQLite-ready dicts.

Handles OpenPositions, Trades, TradeConfirms, and CashTransactions
from FlexQueryResponse XML format.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class FlexXmlResult:
    """Parsed result from a Flex XML response."""

    account_id: str = ""
    report_date: str = ""  # YYYY-MM-DD
    positions: list[dict] = field(default_factory=list)
    trades: list[dict] = field(default_factory=list)
    cash_flows: list[dict] = field(default_factory=list)
    account_snapshot: dict = field(default_factory=dict)


def _safe_float(value: str | None, default: float = 0.0) -> float:
    """Safely convert a string to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _format_date(raw: str | None) -> str:
    """Convert IBKR date to ISO format (YYYY-MM-DD).

    Handles both YYYYMMDD and YYYY-MM-DD formats.
    """
    if not raw:
        return ""
    # Already in YYYY-MM-DD format
    if len(raw) == 10 and raw[4] == '-' and raw[7] == '-':
        return raw
    # YYYYMMDD format
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return raw


def _format_datetime(raw: str | None) -> str:
    """Convert IBKR datetime (YYYYMMDD;HHMMSS) to ISO format."""
    if not raw:
        return ""
    parts = raw.split(";")
    if len(parts) == 2:
        date_part = _format_date(parts[0])
        time_part = parts[1]
        if len(time_part) >= 6:
            return f"{date_part}T{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
    return _format_date(raw)


def parse_flex_xml(xml_path: str | Path) -> list[FlexXmlResult]:
    """Parse a Flex XML file into a list of FlexXmlResult.

    A single XML file may contain multiple FlexStatement elements
    (one per account), so we return a list.
    """
    tree = ET.parse(str(xml_path))
    root = tree.getroot()
    results = []

    for stmt in root.findall(".//FlexStatement"):
        account_id = stmt.get("accountId", "")
        to_date = stmt.get("toDate", "")
        report_date = _format_date(to_date)

        result = FlexXmlResult(
            account_id=account_id,
            report_date=report_date,
        )

        # Parse OpenPositions
        for pos in stmt.findall(".//OpenPositions/OpenPosition"):
            symbol = pos.get("symbol", "")
            if not symbol:
                continue
            currency = pos.get("currency", "USD")
            fx_rate = _safe_float(pos.get("fxRateToBase"), 1.0)
            # Convert to USD if foreign currency
            mark_price = _safe_float(pos.get("markPrice"))
            position_value = _safe_float(pos.get("positionValue"))
            avg_cost = _safe_float(pos.get("averageCost"))
            cost_basis = _safe_float(pos.get("costBasis"))
            pnl_unrealized = _safe_float(pos.get("fifoPnlUnrealized"))
            if currency != "USD" and fx_rate > 0:
                mark_price = mark_price * fx_rate
                position_value = position_value * fx_rate
                avg_cost = avg_cost * fx_rate
                cost_basis = cost_basis * fx_rate
                pnl_unrealized = pnl_unrealized * fx_rate
            result.positions.append({
                "account_id": account_id,
                "report_date": report_date,
                "symbol": symbol,
                "description": pos.get("description", ""),
                "asset_class": pos.get("assetCategory", ""),
                "conid": pos.get("conid", ""),
                "isin": pos.get("isin", ""),
                "listing_exchange": pos.get("listingExchange", ""),
                "currency": currency,
                "fx_rate_to_base": fx_rate,
                "quantity": _safe_float(pos.get("position")),
                "mark_price": mark_price,
                "position_value": position_value,
                "average_cost_price": avg_cost,
                "cost_basis_money": cost_basis,
                "percent_of_nav": _safe_float(pos.get("percentOfNAV")),
                "fifo_pnl_unrealized": pnl_unrealized,
                "total_unrealized_pnl": pnl_unrealized,
            })

        # Parse Trades
        for trade in stmt.findall(".//Trades/Trade"):
            symbol = trade.get("symbol", "")
            if not symbol:
                continue
            currency = trade.get("currency", "USD")
            fx_rate = _safe_float(trade.get("fxRateToBase"), 1.0)
            trade_price = _safe_float(trade.get("tradePrice"))
            trade_money = _safe_float(trade.get("tradeMoney"))
            proceeds = _safe_float(trade.get("proceeds"))
            commission = _safe_float(trade.get("ibCommission"))
            net_cash = _safe_float(trade.get("netCash"))
            pnl_realized = _safe_float(trade.get("fifoPnlRealized"))
            if currency != "USD" and fx_rate > 0:
                trade_price = trade_price * fx_rate
                trade_money = trade_money * fx_rate
                proceeds = proceeds * fx_rate
                commission = commission * fx_rate
                net_cash = net_cash * fx_rate
                pnl_realized = pnl_realized * fx_rate
            result.trades.append({
                "account_id": account_id,
                "symbol": symbol,
                "description": trade.get("description", ""),
                "asset_class": trade.get("assetCategory", ""),
                "conid": trade.get("conid", ""),
                "trade_date": _format_date(trade.get("tradeDate")),
                "date_time": _format_datetime(trade.get("dateTime")),
                "settle_date": _format_date(trade.get("settleDate")),
                "transaction_type": trade.get("transactionType", ""),
                "exchange": trade.get("exchange", ""),
                "currency": currency,
                "fx_rate_to_base": fx_rate,
                "quantity": _safe_float(trade.get("quantity")),
                "trade_price": trade_price,
                "trade_money": trade_money,
                "proceeds": proceeds,
                "taxes": _safe_float(trade.get("taxes")),
                "ib_commission": commission,
                "net_cash": net_cash,
                "fifo_pnl_realized": pnl_realized,
                "buy_sell": trade.get("buySell", ""),
                "order_type": trade.get("orderType", ""),
            })

        # Parse TradeConfirms (today's trades)
        for confirm in stmt.findall(".//TradeConfirms/TradeConfirm"):
            symbol = confirm.get("symbol", "")
            if not symbol:
                continue
            result.trades.append({
                "account_id": account_id,
                "symbol": symbol,
                "description": confirm.get("description", ""),
                "asset_class": confirm.get("assetCategory", ""),
                "conid": confirm.get("conid", ""),
                "trade_date": _format_date(confirm.get("tradeDate")),
                "date_time": _format_datetime(confirm.get("dateTime")),
                "settle_date": _format_date(confirm.get("settleDate")),
                "transaction_type": confirm.get("transactionType", ""),
                "exchange": confirm.get("exchange", ""),
                "quantity": _safe_float(confirm.get("quantity")),
                "trade_price": _safe_float(confirm.get("price")),
                "trade_money": _safe_float(confirm.get("amount")),
                "proceeds": _safe_float(confirm.get("proceeds")),
                "taxes": _safe_float(confirm.get("tax")),
                "ib_commission": _safe_float(confirm.get("commission")),
                "net_cash": _safe_float(confirm.get("netCash")),
                "fifo_pnl_realized": _safe_float(confirm.get("fifoPnlRealized")),
                "buy_sell": confirm.get("buySell", ""),
                "order_type": confirm.get("orderType", ""),
            })

        # Parse CashTransactions
        for ct in stmt.findall(".//CashTransactions/CashTransaction"):
            symbol = ct.get("symbol", "")
            result.cash_flows.append({
                "account_id": account_id,
                "currency": ct.get("currency", "USD"),
                "symbol": symbol or None,
                "description": ct.get("description", ""),
                "date_time": _format_datetime(ct.get("dateTime")),
                "settle_date": _format_date(ct.get("settleDate")),
                "amount": _safe_float(ct.get("amount")),
                "amount_in_base": _safe_float(ct.get("amountInBase")),
                "flow_type": ct.get("type", ""),
                "flow_direction": ct.get("swapType", ""),
                "dividend_type": ct.get("dividendType", ""),
                "transaction_id": ct.get("transactionID", ""),
            })

        # Parse ChangeInNAV for PnL and TWR
        nav = stmt.find(".//ChangeInNAV")
        if nav is not None:
            ending_value = _safe_float(nav.get("endingValue"))
            starting_value = _safe_float(nav.get("startingValue"))
            twr = _safe_float(nav.get("twr"))

            # Compute MTM from starting/ending values (more reliable than mtm field)
            mtm = ending_value - starting_value if starting_value > 0 else _safe_float(nav.get("mtm"))

            # Compute cash: try CashReport first, then estimate from equity - positions
            cash_balance = 0.0
            for cash in stmt.findall(".//CashReport/CashReportBalance"):
                cash_balance += _safe_float(cash.get("endingCash"))

            if cash_balance == 0:
                # Estimate cash from equity minus position values (with FX conversion)
                total_position_value = 0.0
                for pos in stmt.findall(".//OpenPositions/OpenPosition"):
                    val = _safe_float(pos.get("positionValue"))
                    cur = pos.get("currency", "USD")
                    fx = _safe_float(pos.get("fxRateToBase"), 1.0)
                    if cur != "USD" and fx > 0:
                        val = val * fx
                    total_position_value += val
                cash_balance = max(ending_value - total_position_value, 0)

            result.account_snapshot = {
                "account_id": account_id,
                "report_date": report_date,
                "currency": "USD",
                "total_equity": ending_value,
                "cash": cash_balance,
                "stock_value": ending_value - cash_balance,
                "cnav_mtm": mtm,
                "cnav_twr": twr,
                "fifo_total_realized_pnl": 0,
                "fifo_total_unrealized_pnl": mtm,
            }

        logger.info(
            "Parsed Flex XML for %s on %s: %d positions, %d trades, %d cash flows",
            account_id, report_date,
            len(result.positions), len(result.trades), len(result.cash_flows),
        )
        results.append(result)

    return results
