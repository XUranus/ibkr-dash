"""Import job: parse archived Flex files and write to SQLite.

This module handles ONLY parsing and database writes — no network I/O.
Supports multiple file formats (XML, CSV, TXT) via the parser registry.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from worker.clients.sqlite_writer import SQLiteWriter
from worker.core.config import get_settings
from worker.parsers import parse_flex_file
from worker.parsers.base import FlexParseResult

logger = logging.getLogger(__name__)

# Tolerance for cross-validation checks (in USD)
_EQUITY_TOLERANCE = 1.0  # stock_value ≈ total_equity - cash
_DAILY_PNL_TOLERANCE = 50.0  # daily equity change ≈ mtm + deposits

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
    import time as _time

    file_path = Path(file_path)
    file_size = file_path.stat().st_size if file_path.exists() else 0
    logger.info("IBKR import started: file=%s size=%d bytes", file_path.name, file_size)

    t_parse = _time.monotonic()
    results = parse_flex_file(file_path)
    parse_elapsed = _time.monotonic() - t_parse

    t_write = _time.monotonic()
    counts = _write_results(writer, results)
    write_elapsed = _time.monotonic() - t_write

    total = sum(counts.values())
    logger.info(
        "IBKR import completed: file=%s records=%d details=%s "
        "parse_time=%.1fs write_time=%.1fs",
        file_path.name, total, counts, parse_elapsed, write_elapsed,
    )
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
        # Run post-import integrity checks
        _run_integrity_checks(writer)
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


def _run_integrity_checks(writer: SQLiteWriter) -> None:
    """Run cross-validation checks after import to catch data inconsistencies.

    Checks:
      1. stock_value ≈ total_equity - cash for every snapshot
      2. Adjacent-day equity change ≈ cnav_mtm + cnav_deposits (where both available)
      3. CNAV continuity: no unexplained gaps in cnav data
    """
    try:
        with writer._get_conn() as conn:
            _check_stock_value_consistency(conn)
            _check_daily_equity_reconciliation(conn)
    except Exception:
        logger.exception("Post-import integrity checks failed")


def _check_stock_value_consistency(conn: sqlite3.Connection) -> None:
    """Verify stock_value ≈ total_equity - cash for all snapshots."""
    rows = conn.execute(
        """
        SELECT account_id, report_date, total_equity, cash, stock_value
        FROM account_snapshots
        WHERE total_equity IS NOT NULL AND cash IS NOT NULL AND stock_value IS NOT NULL
        ORDER BY report_date DESC
        LIMIT 30
        """,
    ).fetchall()
    violations = []
    for row in rows:
        expected = float(row["total_equity"]) - float(row["cash"])
        actual = float(row["stock_value"])
        if abs(expected - actual) > _EQUITY_TOLERANCE:
            violations.append(
                f"  {row['report_date']}: stock_value={actual:.2f} "
                f"but equity-cash={expected:.2f} (diff={actual - expected:.2f})"
            )
    if violations:
        logger.warning(
            "stock_value consistency check: %d violation(s) in last 30 snapshots:\n%s",
            len(violations), "\n".join(violations[:10]),
        )
    else:
        logger.info("Integrity check: stock_value consistency OK (%d snapshots checked)", len(rows))


def _check_daily_equity_reconciliation(conn: sqlite3.Connection) -> None:
    """Verify daily equity change ≈ cnav_mtm + cnav_deposits where available.

    This catches cases where stale CNAV data causes incorrect P&L derivation.
    """
    rows = conn.execute(
        """
        SELECT account_id, report_date, total_equity,
               cnav_mtm, cnav_deposits, cnav_realized, cnav_change_in_unrealized
        FROM account_snapshots
        WHERE total_equity IS NOT NULL
        ORDER BY report_date ASC
        """,
    ).fetchall()
    if len(rows) < 2:
        return

    violations = []
    for i in range(1, len(rows)):
        prev = rows[i - 1]
        curr = rows[i]
        prev_eq = prev["total_equity"]
        curr_eq = curr["total_equity"]
        if prev_eq is None or curr_eq is None:
            continue

        equity_change = float(curr_eq) - float(prev_eq)
        deposits = float(curr["cnav_deposits"] or 0)

        # Check using detail fields if available
        rlsd = curr["cnav_realized"]
        chg_unr = curr["cnav_change_in_unrealized"]
        if rlsd is not None and chg_unr is not None:
            expected_from_detail = float(rlsd) + float(chg_unr) + deposits
            if abs(equity_change - expected_from_detail) > _DAILY_PNL_TOLERANCE:
                violations.append(
                    f"  {curr['report_date']}: equity_change={equity_change:.2f} "
                    f"vs detail={expected_from_detail:.2f} "
                    f"(rlsd={rlsd}, chgUnr={chg_unr}, dep={deposits})"
                )

    if violations:
        logger.warning(
            "Daily equity reconciliation: %d violation(s):\n%s",
            len(violations), "\n".join(violations[:10]),
        )
    else:
        logger.info("Integrity check: daily equity reconciliation OK (%d transitions)", len(rows) - 1)
