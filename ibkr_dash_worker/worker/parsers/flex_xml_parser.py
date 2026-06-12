"""Parse IBKR Flex Web Service XML responses into SQLite-ready dicts.

Handles OpenPositions, Trades, TradeConfirms, and CashTransactions
from FlexQueryResponse XML format.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from worker.parsers.base import FlexParseResult

logger = logging.getLogger(__name__)

# Backward-compatible alias
FlexXmlResult = FlexParseResult


class FlexXmlParser:
    """Parser for IBKR Flex QueryResponse XML files."""

    @staticmethod
    def can_parse(file_path: Path) -> bool:
        """Check if the file is a Flex XML by extension and root tag."""
        if file_path.suffix.lower() != ".xml":
            return False
        try:
            # Peek at the root tag without loading the full tree
            for event, elem in ET.iterparse(str(file_path), events=("start",)):
                return elem.tag in ("FlexQueryResponse", "FlexStatement")
        except ET.ParseError:
            return False
        return False

    @staticmethod
    def parse(file_path: Path) -> list[FlexParseResult]:
        """Parse a Flex XML file into standardized results."""
        return parse_flex_xml(file_path)


import re as _re

# Month name mapping for dd-MMM-yy format
_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _safe_float(value: str | None, default: float = 0.0) -> float:
    """Safely convert a string to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _format_date(raw: str | None) -> str:
    """Convert various date formats to ISO (YYYY-MM-DD).

    Supported formats:
      YYYYMMDD        (20260611)
      YYYY-MM-dd      (2026-06-11)
      MM/dd/yy        (06/11/26)
      MM/dd/yyyy      (06/11/2026)
      dd/MM/yy        (11/06/26)
      dd/MM/yyyy      (11/06/2026)
      dd-MMM-yy      (11-Jun-26)
      dd-MMM-yyyy    (11-Jun-2026)
    """
    if not raw:
        return ""
    raw = raw.strip()

    # Already ISO: YYYY-MM-dd
    if _re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw

    # YYYYMMDD
    if _re.match(r"^\d{8}$", raw):
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"

    # dd-MMM-yy or dd-MMM-yyyy (e.g., 11-Jun-26, 11-Jun-2026)
    m = _re.match(r"^(\d{1,2})-([A-Za-z]{3})-(\d{2,4})$", raw)
    if m:
        day, mon_str, year = m.groups()
        mon = _MONTH_MAP.get(mon_str.lower())
        if mon:
            yr = int(year)
            if yr < 100:
                yr += 2000
            return f"{yr}-{mon:02d}-{int(day):02d}"

    # Slash-separated: MM/dd/yy, MM/dd/yyyy, dd/MM/yy, dd/MM/yyyy
    if "/" in raw:
        parts = raw.split("/")
        if len(parts) == 3:
            a, b, c = parts
            a, b = int(a), int(b)
            yr = int(c)
            if yr < 100:
                yr += 2000
            # Heuristic: if first part > 12, it's dd/MM; otherwise MM/dd
            if a > 12:
                return f"{yr}-{b:02d}-{a:02d}"
            else:
                return f"{yr}-{a:02d}-{b:02d}"

    return raw


def _format_datetime(raw: str | None) -> str:
    """Convert various datetime formats to ISO (YYYY-MM-ddTHH:MM:SS).

    Supported separators between date and time: ;, space, T
    Supported time formats:
      HHmmss           (143022)
      HH:mm:ss         (14:30:22)
      HH:mm:ss TZ      (14:30:22 EST)
      HH:mm TZ         (14:30 EST)
    """
    if not raw:
        return ""
    raw = raw.strip()

    # Split on ; or T or space (but not timezone abbreviations)
    # Try common separators
    date_part = raw
    time_part = ""
    for sep in [";", "T"]:
        if sep in raw:
            date_part, time_part = raw.split(sep, 1)
            break
    # Try space separator only if the second part looks like a time
    if not time_part and " " in raw:
        parts = raw.split()
        if len(parts) >= 2 and ":" in parts[1]:
            date_part = parts[0]
            time_part = " ".join(parts[1:])

    date_iso = _format_date(date_part)
    if not time_part:
        return date_iso

    time_part = time_part.strip()
    # Strip timezone suffix (e.g., " EST", " +0800")
    time_clean = _re.sub(r"\s*[A-Z]{2,4}$", "", time_part).strip()
    time_clean = _re.sub(r"\s*[+-]\d{4}$", "", time_clean).strip()

    # HHmmss (6 digits)
    if _re.match(r"^\d{6}$", time_clean):
        return f"{date_iso}T{time_clean[:2]}:{time_clean[2:4]}:{time_clean[4:6]}"

    # HHmm (4 digits, no seconds)
    if _re.match(r"^\d{4}$", time_clean):
        return f"{date_iso}T{time_clean[:2]}:{time_clean[2:4]}:00"

    # HH:mm:ss or HH:mm
    if ":" in time_clean:
        parts = time_clean.split(":")
        h = parts[0].zfill(2)
        m = parts[1].zfill(2) if len(parts) > 1 else "00"
        s = parts[2].zfill(2) if len(parts) > 2 else "00"
        return f"{date_iso}T{h}:{m}:{s}"

    return date_iso


def parse_flex_xml(xml_path: str | Path) -> list[FlexParseResult]:
    """Parse a Flex XML file into a list of FlexParseResult.

    A single XML file may contain multiple FlexStatement elements
    (one per account/date), so we return a list.
    """
    tree = ET.parse(str(xml_path))
    root = tree.getroot()
    results = []

    for stmt in root.findall(".//FlexStatement"):
        account_id = stmt.get("accountId", "")
        to_date = stmt.get("toDate", "")
        report_date = _format_date(to_date)

        result = FlexParseResult(
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
            cost_basis = _safe_float(pos.get("costBasis")) or _safe_float(pos.get("costBasisMoney"))
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

            # Compute cumulative MTM from starting/ending values.
            # This includes deposits/withdrawals; the chart service will
            # compute the true daily MTM by subtracting consecutive days
            # and adjusting for deposits.
            mtm = ending_value - starting_value if starting_value > 0 else _safe_float(nav.get("mtm"))

            # Daily deposit/withdrawal amount (for daily MTM adjustment)
            deposits = _safe_float(nav.get("depositsWithdrawals"))

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
                "cnav_deposits": deposits,
                "cnav_starting_value": starting_value,
                "cnav_ending_value": ending_value,
                "cnav_realized": _safe_float(nav.get("realized")),
                "cnav_change_in_unrealized": _safe_float(nav.get("changeInUnrealized")),
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
