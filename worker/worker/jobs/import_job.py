"""Import job: parse archived Flex files and write to SQLite.

This module handles ONLY parsing and database writes — no network I/O.
Supports multiple file formats (XML, CSV, TXT) via the parser registry.
"""

from __future__ import annotations

import logging
from pathlib import Path

from worker.clients.sqlite_writer import SQLiteWriter
from worker.core.config import get_settings
from worker.parsers import parse_flex_file
from worker.parsers.base import FlexParseResult

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

IMPORTED_FILES_LOG = "imported_files.txt"


def _get_imported_files(data_dir: Path) -> set[str]:
    """Read the set of already-imported file names from the tracking file."""
    log_path = data_dir / IMPORTED_FILES_LOG
    if not log_path.exists():
        return set()
    return {
        line.strip()
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def _mark_imported(data_dir: Path, file_name: str) -> None:
    """Append a file name to the tracking file."""
    log_path = data_dir / IMPORTED_FILES_LOG
    with log_path.open("a", encoding="utf-8") as f:
        f.write(file_name + "\n")


def _write_results(writer: SQLiteWriter, results: list[FlexParseResult]) -> dict[str, int]:
    """Write parsed results to SQLite.

    Returns:
        Dict with counts of records written per table.
    """
    counts: dict[str, int] = {
        "account_snapshots": 0,
        "position_snapshots": 0,
        "trade_records": 0,
        "cash_flows": 0,
    }

    for result in results:
        if result.account_snapshot:
            writer.upsert_account_snapshot(result.account_snapshot)
            counts["account_snapshots"] += 1
        elif result.positions:
            # Build snapshot from positions if no ChangeInNAV data
            total_value = sum(p.get("position_value", 0) or 0 for p in result.positions)
            writer.upsert_account_snapshot({
                "account_id": result.account_id,
                "report_date": result.report_date,
                "currency": "USD",
                "total_equity": total_value,
                "cash": 0,
                "stock_value": total_value,
            })
            counts["account_snapshots"] += 1

        if result.positions:
            n = writer.bulk_upsert_positions(result.positions)
            counts["position_snapshots"] += n

        if result.trades:
            for trade in result.trades:
                writer.insert_trade(trade)
            counts["trade_records"] += len(result.trades)

        if result.cash_flows:
            for cf in result.cash_flows:
                writer.insert_cash_flow(cf)
            counts["cash_flows"] += len(result.cash_flows)

    return counts


def import_flex_file(
    writer: SQLiteWriter,
    file_path: Path | str,
) -> dict[str, int]:
    """Parse a single Flex file and import into SQLite.

    Auto-detects format (XML/CSV/TXT) via the parser registry.

    Args:
        writer: Initialized SQLiteWriter instance.
        file_path: Path to the Flex file.

    Returns:
        Dict with counts of records imported per table.
    """
    file_path = Path(file_path)
    logger.info("Importing %s", file_path.name)

    results = parse_flex_file(file_path)
    counts = _write_results(writer, results)

    total = sum(counts.values())
    logger.info("Imported %s: %d records (%s)", file_path.name, total, counts)
    return counts


def import_all_archived(
    data_dir: Path | str | None = None,
    sqlite_path: str | None = None,
    force: bool = False,
) -> dict[str, dict[str, int]]:
    """Import all unprocessed Flex files from the data directory.

    Scans for XML, CSV, and TXT files. Tracks which files have been
    imported to avoid re-processing.

    Args:
        data_dir: Directory to scan. Defaults to settings.data_dir.
        sqlite_path: SQLite database path. Defaults to settings.sqlite_path.
        force: If True, re-import all files ignoring the tracking file.

    Returns:
        Dict mapping filename to import result counts.
    """
    settings = get_settings()
    data_dir = Path(data_dir or settings.data_dir)
    writer = SQLiteWriter(sqlite_path or settings.sqlite_path)
    writer.init_schema()

    imported_names = set() if force else _get_imported_files(data_dir)
    all_results: dict[str, dict[str, int]] = {}

    # Scan for all supported file types, excluding the tracking file
    skip_names = {IMPORTED_FILES_LOG}
    for pattern in ("*.xml", "*.csv", "*.txt"):
        for file_path in sorted(data_dir.glob(pattern)):
            if file_path.name in imported_names or file_path.name in skip_names:
                continue

            try:
                counts = import_flex_file(writer, file_path)
                all_results[file_path.name] = counts
                _mark_imported(data_dir, file_path.name)
            except Exception:
                logger.exception("Failed to import %s", file_path.name)

    if all_results:
        logger.info("Imported %d new files", len(all_results))
        # Trigger position analysis in background (non-blocking)
        _trigger_position_analysis()
    else:
        logger.info("No new files to import")

    return all_results


def _trigger_position_analysis() -> None:
    """Trigger position analysis via backend API (non-blocking)."""
    try:
        from worker.clients.position_analysis_client import trigger_position_analysis
        settings = get_settings()
        trigger_position_analysis(settings)
    except Exception as exc:
        logger.debug("Position analysis trigger skipped: %s", exc)
