"""Import a single IBKR Flex CSV file into SQLite.

Parses the CSV, transforms the data, and upserts all record types
(account snapshots, positions, trades, cash flows, price history).
"""

from __future__ import annotations

import logging
from pathlib import Path

from worker.clients.sqlite_writer import SQLiteWriter
from worker.core.config import get_settings
from worker.parsers.flex_csv_parser import parse_flex_csv
from worker.parsers.transformers import transform_daily_statement

logger = logging.getLogger(__name__)


def import_daily_snapshot_file(
    writer: SQLiteWriter,
    file_path: str | Path,
) -> dict[str, int]:
    """Parse and import a single Flex CSV file into SQLite.

    Args:
        writer: An initialized SQLiteWriter instance.
        file_path: Path to the Flex CSV file.

    Returns:
        A dict mapping entity type to the number of records upserted.
    """
    path = Path(file_path)
    logger.info("Importing daily snapshot from %s", path)

    statement = parse_flex_csv(path)
    result = transform_daily_statement(statement)

    counts: dict[str, int] = {}
    counts["account_snapshots"] = writer.bulk_upsert_account_snapshots(
        result.account_documents
    )
    counts["position_snapshots"] = writer.bulk_upsert_positions(
        result.position_documents
    )
    counts["trade_records"] = writer.bulk_upsert_trades(
        result.trade_documents
    )
    counts["cash_flows"] = writer.bulk_upsert_cash_flows(
        result.cash_flow_documents
    )
    counts["price_history"] = writer.bulk_upsert_price_history(
        result.price_history_documents
    )

    total = sum(counts.values())
    logger.info(
        "Import complete for %s: %d total records (%s)",
        path.name,
        total,
        counts,
    )
    return counts
