"""Parse IBKR Flex Web Service XML responses into SQLite-ready dicts.

Handles OpenPositions, Trades, TradeConfirms, and CashTransactions
from FlexQueryResponse XML format.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from worker.parsers.base import FlexParseResult

OPTION_MULTIPLIER = 100  # 1 options contract = 100 shares

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
    """Safely convert a string to float. Returns *default* when value is None."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _optional_float(value: str | None) -> float | None:
    """Convert a string to float, returning *None* when the field is absent.

    Use this for ChangeInNAV component fields so the writer can distinguish
    "IBKR returned 0" (write 0) from "field missing" (preserve old value).
    """
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


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

        # Parse OpenPositions (SUMMARY only — skip LOT-level duplicates)
        for pos in stmt.findall(".//OpenPositions/OpenPosition"):
            symbol = pos.get("symbol", "")
            if not symbol:
                continue
            level = pos.get("levelOfDetail", "")
            if level and level.upper() != "SUMMARY":
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
            asset_class = pos.get("assetCategory", "")
            raw_quantity = _safe_float(pos.get("position"))

            # Options: IBKR reports quantity in contracts (1 contract = 100 shares)
            # Convert to shares for consistent display
            if asset_class == "OPT":
                raw_quantity = raw_quantity * OPTION_MULTIPLIER
                avg_cost = avg_cost / OPTION_MULTIPLIER if avg_cost > 0 else avg_cost
                cost_basis = cost_basis  # cost_basis is already total value

            # NOTE: Do NOT trust IBKR's percentOfNAV — it is unreliable for
            # options and some other instruments.  We compute it ourselves
            # after all positions are collected (see nav patch below).

            result.positions.append({
                "account_id": account_id,
                "report_date": report_date,
                "symbol": symbol,
                "description": pos.get("description", ""),
                "asset_class": asset_class,
                "conid": pos.get("conid", ""),
                "isin": pos.get("isin", ""),
                "listing_exchange": pos.get("listingExchange", ""),
                "currency": currency,
                "fx_rate_to_base": fx_rate,
                "quantity": raw_quantity,
                "mark_price": mark_price,
                "position_value": position_value,
                "average_cost_price": avg_cost,
                "cost_basis_money": cost_basis,
                "percent_of_nav": 0.0,  # recomputed below
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
                "trade_id": trade.get("tradeID", ""),
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
                "trade_id": confirm.get("tradeID", ""),
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

        # Parse CashTransactions (skip SUMMARY entries to avoid double-counting)
        for ct in stmt.findall(".//CashTransactions/CashTransaction"):
            if ct.get("levelOfDetail", "").upper() == "SUMMARY":
                continue
            symbol = ct.get("symbol", "")
            amount = _safe_float(ct.get("amount"))
            currency = ct.get("currency", "USD")
            fx_rate = _safe_float(ct.get("fxRateToBase"), 1.0)
            # amountInBase may not exist; compute from amount * fxRateToBase
            amount_in_base = _safe_float(ct.get("amountInBase"))
            if amount_in_base == 0 and amount != 0:
                amount_in_base = amount * fx_rate if currency != "USD" and fx_rate > 0 else amount
            result.cash_flows.append({
                "account_id": account_id,
                "currency": currency,
                "symbol": symbol or None,
                "description": ct.get("description", ""),
                "date_time": _format_datetime(ct.get("dateTime")),
                "settle_date": _format_date(ct.get("settleDate")),
                "amount": amount,
                "amount_in_base": amount_in_base,
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

            # Skip snapshots for inactive/empty accounts (equity = 0).
            # IBKR returns ChangeInNAV with endingValue=0 for periods before
            # the account was funded — these are ghost snapshots that pollute
            # the performance calendar with false "no change" entries.
            if ending_value <= 0:
                logger.info(
                    "Skipping ChangeInNAV for %s on %s: ending_value=%.2f (account inactive)",
                    account_id, report_date, ending_value,
                )
            else:
                twr = _safe_float(nav.get("twr"))

                # Read raw component values from the Flex report.
                # Use _optional_float so that "field absent" → None (distinct from 0).
                # The writer's UPSERT uses IS NOT NULL guards: None preserves old
                # values, while 0.0 is written through as a genuine zero.
                raw_mtm = _optional_float(nav.get("mtm"))
                raw_realized = _optional_float(nav.get("realized"))
                raw_chg_unr = _optional_float(nav.get("changeInUnrealized"))
                deposits = _safe_float(nav.get("depositsWithdrawals"))

                # Compute daily equity change
                daily_change = ending_value - starting_value if starting_value > 0 else 0

                # Detect incomplete Flex report: IBKR sometimes returns all-zero
                # component breakdown (mtm=0, realized=0, changeInUnrealized=0)
                # while the startingValue and endingValue are correct.
                # In this case, infer the breakdown from the daily change.
                mtm_val = raw_mtm or 0.0
                rlsd_val = raw_realized or 0.0
                chg_unr_val = raw_chg_unr or 0.0
                is_incomplete = (
                    raw_mtm is not None and abs(mtm_val) < 0.01
                    and raw_realized is not None and abs(rlsd_val) < 0.01
                    and raw_chg_unr is not None and abs(chg_unr_val) < 0.01
                    and abs(daily_change) > 1.0
                )

                if is_incomplete:
                    # Incomplete report: infer changeInUnrealized from daily change
                    # Formula: daily_change = realized + changeInUnrealized + deposits
                    inferred_chg_unr = daily_change - rlsd_val - deposits
                    mtm = inferred_chg_unr  # best approximation
                    realized = rlsd_val
                    change_in_unrealized = inferred_chg_unr
                    logger.warning(
                        "Incomplete ChangeInNAV for %s on %s: "
                        "components all zero but daily_change=%.2f. "
                        "Inferring changeInUnrealized=%.2f",
                        account_id, report_date, daily_change, inferred_chg_unr,
                    )
                else:
                    mtm = raw_mtm
                    realized = raw_realized
                    change_in_unrealized = raw_chg_unr

                # Cross-validate: endingValue - startingValue should ≈ realized + changeInUnrealized + deposits
                if starting_value > 0 and realized is not None and change_in_unrealized is not None:
                    expected = realized + change_in_unrealized + deposits
                    discrepancy = daily_change - expected
                    if abs(discrepancy) > 5.0:
                        logger.info(
                            "ChangeInNAV reconciliation for %s on %s: "
                            "daily_change=%.2f, components=%.2f (realized=%.2f + chgUnr=%.2f + deposits=%.2f), "
                            "discrepancy=%.2f (likely fees/interest/dividends)",
                            account_id, report_date,
                            daily_change, expected, realized, change_in_unrealized, deposits,
                            discrepancy,
                        )

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

                # Compute cumulative unrealized PnL from position-level data.
                cumulative_unrealized = sum(
                    p.get("fifo_pnl_unrealized", 0) or 0 for p in result.positions
                )

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
                    "cnav_realized": realized,
                    "cnav_change_in_unrealized": change_in_unrealized,
                    "fifo_total_realized_pnl": 0,
                    "fifo_total_unrealized_pnl": cumulative_unrealized,
                }

                # Recompute percent_of_nav using actual total equity.
                # IBKR's percentOfNAV is unreliable for options and some other
                # instruments (can report values > 100% or wildly incorrect).
                for p in result.positions:
                    p["percent_of_nav"] = round(
                        (p["position_value"] / ending_value) * 100, 2
                    )

        # Fallback: if no ChangeInNAV was found (ending_value still 0),
        # compute percent_of_nav from sum of absolute position values.
        if result.positions:
            total_abs = sum(abs(p["position_value"]) for p in result.positions)
            if total_abs > 0 and all(p["percent_of_nav"] == 0 for p in result.positions):
                for p in result.positions:
                    p["percent_of_nav"] = round(
                        (p["position_value"] / total_abs) * 100, 2
                    )

        logger.info(
            "Parsed Flex XML for %s on %s: %d positions, %d trades, %d cash flows",
            account_id, report_date,
            len(result.positions), len(result.trades), len(result.cash_flows),
        )
        results.append(result)

        # Parse EquitySummaryByReportDateInBase for additional daily snapshots.
        # ChangeInNAV only covers the report_date; EquitySummary has data for
        # many prior dates.  We create extra FlexParseResult entries for dates
        # not already covered so that the writer can fill gaps.
        seen_dates = {report_date}
        for eq in stmt.findall(".//EquitySummaryByReportDateInBase"):
            eq_date = _format_date(eq.get("reportDate"))
            if not eq_date or eq_date in seen_dates:
                continue
            seen_dates.add(eq_date)
            eq_total = _safe_float(eq.get("total"))
            eq_cash = _safe_float(eq.get("cash"))
            eq_stock = _safe_float(eq.get("stock"))
            eq_options = _safe_float(eq.get("options"))
            eq_funds = _safe_float(eq.get("funds"))
            eq_crypto = _safe_float(eq.get("crypto"))
            if eq_total <= 0:
                continue
            eq_result = FlexParseResult(
                account_id=account_id,
                report_date=eq_date,
            )
            eq_result.account_snapshot = {
                "account_id": account_id,
                "report_date": eq_date,
                "currency": "USD",
                "total_equity": eq_total,
                "cash": eq_cash,
                "stock_value": eq_stock,
                "options_value": eq_options,
                "funds_value": eq_funds,
                "crypto_value": eq_crypto,
            }
            results.append(eq_result)

    return results
