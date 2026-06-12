"""Parser for IBKR Flex Query CSV reports.

IBKR Flex exports use a multi-section CSV format with record type markers:
  BOF  - Beginning of file (metadata)
  BOA  - Beginning of account (key-value metadata pairs)
  BOS  - Beginning of section
  HEADER - Column headers for the current section
  DATA   - A data row in the current section
  EOS  - End of section
  EOF  - End of file

Sections include: ACCT, EQUT, POST, TRNT, CTRN, FIFO, MYTD, NETP, SECU, PPPO, etc.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from csv import reader as csv_reader
from pathlib import Path

from worker.parsers.base import FlexParseResult
from worker.utils.dates import to_iso_date
from worker.utils.numbers import clean_string

logger = logging.getLogger(__name__)


class FlexCsvParser:
    """Parser for IBKR Flex Query CSV files.

    Implements the FlexParser protocol. The CSV format requires two passes:
    1. parse_flex_csv() builds a FlexStatement (section-based structure)
    2. _transform_to_results() converts sections into FlexParseResult dicts
    """

    @staticmethod
    def can_parse(file_path: Path) -> bool:
        """Check if the file is a Flex CSV by extension and first-line content."""
        if file_path.suffix.lower() not in (".csv", ".txt"):
            return False
        try:
            with file_path.open("r", encoding="utf-8-sig") as f:
                first_line = f.readline().strip().upper()
                return first_line.startswith("BOF") or first_line.startswith("BOA")
        except (OSError, UnicodeDecodeError):
            return False

    @staticmethod
    def parse(file_path: Path) -> list[FlexParseResult]:
        """Parse a Flex CSV file into standardized results."""
        statement = parse_flex_csv(file_path)
        return _transform_to_results(statement)


@dataclass
class FlexSection:
    """A parsed section from the Flex CSV."""
    name: str
    headers: list[str] = field(default_factory=list)
    rows: list[dict[str, str | None]] = field(default_factory=list)


@dataclass
class FlexStatementMetadata:
    """Metadata extracted from BOF/BOA records."""
    query_name: str | None
    from_date: str | None
    to_date: str | None
    account_ids: list[str]
    raw: dict[str, str | None] = field(default_factory=dict)


@dataclass
class FlexStatement:
    """A fully parsed Flex CSV statement."""
    source_file: Path
    metadata: FlexStatementMetadata
    sections: dict[str, FlexSection]
    record_counts: dict[str, int]

    def get_section(self, section_name: str) -> FlexSection | None:
        """Return a section by name, or None if not present."""
        return self.sections.get(section_name)


def _normalize_row(row: list[str]) -> list[str]:
    """Strip whitespace from every cell in a row."""
    return [column.strip() for column in row]


def _strip_leading_section_name(
    payload: list[str], section_name: str | None
) -> list[str]:
    """Remove the leading section name cell if present."""
    if section_name and payload and payload[0].strip().upper() == section_name.upper():
        return payload[1:]
    return payload


def _pairwise_metadata(payload: list[str]) -> dict[str, str | None]:
    """Interpret payload cells as key-value pairs."""
    metadata: dict[str, str | None] = {}
    for index in range(0, len(payload) - 1, 2):
        key = clean_string(payload[index])
        if key is None:
            continue
        metadata[key] = clean_string(payload[index + 1])
    return metadata


def _find_value(
    row: dict[str, str | None], aliases: tuple[str, ...]
) -> str | None:
    """Look up a value in a row dict by trying multiple case-insensitive aliases."""
    normalized = {key.lower(): value for key, value in row.items()}
    for alias in aliases:
        if alias.lower() in normalized and normalized[alias.lower()]:
            return normalized[alias.lower()]
    return None


def _extract_metadata(
    sections: dict[str, FlexSection],
    raw_metadata: dict[str, str | None],
) -> FlexStatementMetadata:
    """Build FlexStatementMetadata from parsed sections and raw metadata."""
    account_ids: list[str] = []
    acct_section = sections.get("ACCT")
    if acct_section:
        for row in acct_section.rows:
            account_id = _find_value(
                row, ("AccountId", "Account", "ClientAccountID", "Account ID")
            )
            if account_id and account_id not in account_ids:
                account_ids.append(account_id)

    query_name = raw_metadata.get("QueryName")
    from_date = raw_metadata.get("FromDate")
    to_date = raw_metadata.get("ToDate")

    if acct_section and acct_section.rows:
        first_row = acct_section.rows[0]
        query_name = query_name or _find_value(first_row, ("QueryName", "StatementName"))
        from_date = from_date or _find_value(first_row, ("FromDate", "PeriodStartDate"))
        to_date = to_date or _find_value(first_row, ("ToDate", "PeriodEndDate", "ReportDate"))

    return FlexStatementMetadata(
        query_name=query_name,
        from_date=to_iso_date(from_date),
        to_date=to_iso_date(to_date),
        account_ids=account_ids,
        raw=raw_metadata,
    )


def parse_flex_csv(file_path: str | Path) -> FlexStatement:
    """Parse an IBKR Flex Query CSV file into a FlexStatement.

    Args:
        file_path: Path to the Flex CSV file.

    Returns:
        A FlexStatement with all sections, metadata, and record counts.
    """
    source_file = Path(file_path)
    sections: dict[str, FlexSection] = {}
    record_counts: Counter[str] = Counter()
    raw_metadata: dict[str, str | None] = {}
    current_section_name: str | None = None

    with source_file.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv_reader(handle)
        for raw_row in reader:
            normalized_row = _normalize_row(raw_row)
            if not any(normalized_row):
                continue

            record_type = normalized_row[0].upper()
            payload = normalized_row[1:]
            record_counts[record_type] += 1

            if record_type == "BOA":
                raw_metadata.update(_pairwise_metadata(payload))
                continue

            if record_type == "BOF":
                if len(payload) >= 1 and "AccountId" not in raw_metadata:
                    raw_metadata["AccountId"] = clean_string(payload[0])
                if len(payload) >= 2 and "QueryName" not in raw_metadata:
                    raw_metadata["QueryName"] = clean_string(payload[1])
                if len(payload) >= 4 and "FromDate" not in raw_metadata:
                    raw_metadata["FromDate"] = clean_string(payload[3])
                if len(payload) >= 5 and "ToDate" not in raw_metadata:
                    raw_metadata["ToDate"] = clean_string(payload[4])
                continue

            if record_type == "BOS":
                current_section_name = clean_string(payload[0]) if payload else None
                if current_section_name is None:
                    current_section_name = f"UNKNOWN_SECTION_{len(sections) + 1}"
                sections.setdefault(
                    current_section_name, FlexSection(name=current_section_name)
                )
                continue

            if record_type == "HEADER" and current_section_name:
                header_values = _strip_leading_section_name(payload, current_section_name)
                sections[current_section_name].headers = header_values
                continue

            if record_type == "DATA" and current_section_name:
                section = sections[current_section_name]
                data_values = _strip_leading_section_name(payload, current_section_name)
                row_dict: dict[str, str | None] = {}

                for index, header in enumerate(section.headers):
                    value = data_values[index] if index < len(data_values) else ""
                    row_dict[header] = clean_string(value)

                if len(data_values) > len(section.headers):
                    extras = data_values[len(section.headers):]
                    for offset, extra_value in enumerate(extras, start=1):
                        row_dict[f"__extra_{offset}"] = clean_string(extra_value)

                section.rows.append(row_dict)
                continue

            if record_type == "EOS":
                current_section_name = None

    metadata = _extract_metadata(sections, raw_metadata)
    return FlexStatement(
        source_file=source_file,
        metadata=metadata,
        sections=sections,
        record_counts=dict(record_counts),
    )


# ---------------------------------------------------------------------------
# Transform FlexStatement → FlexParseResult
# ---------------------------------------------------------------------------

def _safe_float(value: str | None, default: float = 0.0) -> float:
    """Safely convert a string to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _row_lookup(row: dict[str, str | None]) -> dict[str, str | None]:
    """Build case-insensitive lookup from a row dict."""
    import re
    return {re.sub(r"[^a-z0-9]+", "", key.lower()): value for key, value in row.items()}


def _get(row: dict[str, str | None], *aliases: str) -> str | None:
    """Get a value from a row by trying multiple case-insensitive aliases."""
    lookup = _row_lookup(row)
    for alias in aliases:
        normalized = re.sub(r"[^a-z0-9]+", "", alias.lower()) if 're' in dir() else alias.lower()
        import re as _re
        normalized = _re.sub(r"[^a-z0-9]+", "", alias.lower())
        value = lookup.get(normalized)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _get_num(row: dict[str, str | None], *aliases: str) -> float | None:
    """Get a numeric value from a row by trying multiple aliases."""
    val = _get(row, *aliases)
    return _safe_float(val) if val is not None else None


def _first_row(section: FlexSection | None) -> dict[str, str | None]:
    """Get the first row of a section, or empty dict."""
    if section and section.rows:
        return section.rows[0]
    return {}


def _transform_to_results(statement: FlexStatement) -> list[FlexParseResult]:
    """Transform a parsed FlexStatement into FlexParseResult dicts.

    This merges the parsing and transformation steps, producing
    standardized records ready for the writer layer.
    """
    import re as _re

    results: list[FlexParseResult] = []
    account_ids = statement.metadata.account_ids or ["UNKNOWN"]
    report_date = statement.metadata.to_date or ""

    for account_id in account_ids:
        result = FlexParseResult(
            account_id=account_id,
            report_date=report_date,
        )

        # --- Account snapshot from EQUT section ---
        equt = statement.get_section("EQUT")
        equt_row = _first_row(equt)
        if equt_row:
            result.account_snapshot = {
                "account_id": account_id,
                "report_date": report_date,
                "currency": _get(equt_row, "Currency", "CurrencyPrimary", "BaseCurrency") or "USD",
                "total_equity": _get_num(equt_row, "TotalEquity", "Total", "EndingSettledValue", "NetLiquidationValue"),
                "cash": _get_num(equt_row, "Cash"),
                "stock_value": _get_num(equt_row, "StockValue", "Stock", "Stocks"),
                "options_value": _get_num(equt_row, "OptionsValue", "Options"),
                "funds_value": _get_num(equt_row, "FundsValue", "Funds"),
                "crypto_value": _get_num(equt_row, "CryptoValue", "Crypto"),
            }

        # --- ChangeInNAV section ---
        cnav = statement.get_section("ChangeInNAV")
        cnav_row = _first_row(cnav)
        if cnav_row and result.account_snapshot:
            starting = _get_num(cnav_row, "StartingValue", "BeginningValue") or 0
            ending = _get_num(cnav_row, "EndingValue", "EndingNAV") or 0
            mtm = ending - starting if starting > 0 else _get_num(cnav_row, "MTM", "MarkToMarket") or 0
            result.account_snapshot.update({
                "cnav_mtm": mtm,
                "cnav_twr": _get_num(cnav_row, "TWR", "TimeWeightedReturn"),
                "cnav_deposits": _get_num(cnav_row, "DepositsWithdrawals"),
                "cnav_starting_value": starting,
                "cnav_ending_value": ending,
                "cnav_realized": _get_num(cnav_row, "Realized"),
                "cnav_change_in_unrealized": _get_num(cnav_row, "ChangeInUnrealized"),
                "fifo_total_realized_pnl": 0,
                "fifo_total_unrealized_pnl": mtm,
            })

        # --- Positions from POST section ---
        post = statement.get_section("POST")
        if post:
            for row in post.rows:
                symbol = _get(row, "Symbol")
                if not symbol:
                    continue
                result.positions.append({
                    "account_id": account_id,
                    "report_date": report_date,
                    "symbol": symbol,
                    "description": _get(row, "Description"),
                    "asset_class": _get(row, "AssetClass", "Asset Category"),
                    "conid": _get(row, "Conid"),
                    "quantity": _get_num(row, "Position", "Quantity"),
                    "mark_price": _get_num(row, "MarkPrice", "Mark Price"),
                    "position_value": _get_num(row, "PositionValue", "Position Value"),
                    "average_cost_price": _get_num(row, "AverageCost", "Average Cost"),
                    "cost_basis_money": _get_num(row, "CostBasis", "Cost Basis", "CostBasisMoney"),
                    "percent_of_nav": _get_num(row, "PercentOfNAV", "Percent Of NAV"),
                    "fifo_pnl_unrealized": _get_num(row, "FifoPnlUnrealized", "FIFO PnL Unrealized"),
                    "total_unrealized_pnl": _get_num(row, "FifoPnlUnrealized", "FIFO PnL Unrealized"),
                    "total_realized_pnl": _get_num(row, "RealizedPnL", "Realized PnL"),
                    "previous_day_change_percent": _get_num(row, "PreviousDayChangePct"),
                })

        # --- Trades from TRNT section ---
        trnt = statement.get_section("TRNT")
        if trnt:
            for row in trnt.rows:
                symbol = _get(row, "Symbol")
                if not symbol:
                    continue
                result.trades.append({
                    "account_id": account_id,
                    "symbol": symbol,
                    "description": _get(row, "Description"),
                    "asset_class": _get(row, "AssetClass", "Asset Category"),
                    "conid": _get(row, "Conid"),
                    "trade_date": to_iso_date(_get(row, "TradeDate", "Trade Date")),
                    "date_time": _get(row, "DateTime", "Date/Time"),
                    "settle_date": to_iso_date(_get(row, "SettleDate", "Settle Date")),
                    "transaction_type": _get(row, "TransactionType", "Transaction Type"),
                    "exchange": _get(row, "Exchange"),
                    "currency": _get(row, "Currency") or "USD",
                    "quantity": _get_num(row, "Quantity"),
                    "trade_price": _get_num(row, "TradePrice", "Trade Price"),
                    "trade_money": _get_num(row, "TradeMoney", "Trade Money"),
                    "proceeds": _get_num(row, "Proceeds"),
                    "taxes": _get_num(row, "Taxes"),
                    "ib_commission": _get_num(row, "IBCommission", "IB Commission", "Commission"),
                    "net_cash": _get_num(row, "NetCash", "Net Cash"),
                    "fifo_pnl_realized": _get_num(row, "FifoPnlRealized", "FIFO PnL Realized"),
                    "buy_sell": _get(row, "BuySell", "Buy/Sell"),
                    "order_type": _get(row, "OrderType", "Order Type"),
                })

        # --- Cash flows from CTRN section ---
        ctrn = statement.get_section("CTRN")
        if ctrn:
            for row in ctrn.rows:
                result.cash_flows.append({
                    "account_id": account_id,
                    "currency": _get(row, "Currency") or "USD",
                    "symbol": _get(row, "Symbol"),
                    "description": _get(row, "Description"),
                    "date_time": _get(row, "DateTime", "Date/Time"),
                    "settle_date": to_iso_date(_get(row, "SettleDate", "Settle Date")),
                    "amount": _get_num(row, "Amount"),
                    "amount_in_base": _get_num(row, "AmountInBase", "Amount In Base"),
                    "flow_type": _get(row, "Type", "ActivityCode"),
                    "flow_direction": _get(row, "SwapType"),
                    "dividend_type": _get(row, "DividendType"),
                    "transaction_id": _get(row, "TransactionID"),
                })

        logger.info(
            "Parsed Flex CSV for %s on %s: %d positions, %d trades, %d cash flows",
            account_id, report_date,
            len(result.positions), len(result.trades), len(result.cash_flows),
        )
        results.append(result)

    return results
