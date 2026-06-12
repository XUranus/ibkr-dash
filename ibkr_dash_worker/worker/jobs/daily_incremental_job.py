"""Daily incremental import job.

Pulls data from IBKR Flex Web Service, saves XML to data_dir,
parses it, and imports into SQLite. Also scans data_dir for
any manually placed CSV files.
"""

from __future__ import annotations

import logging
from pathlib import Path

from worker.clients.flex_client import FlexClient, FlexClientError
from worker.clients.sqlite_writer import SQLiteWriter
from worker.core.config import get_settings
from worker.jobs.import_daily_snapshot import import_daily_snapshot_file
from worker.parsers.flex_xml_parser import parse_flex_xml

logger = logging.getLogger(__name__)

IMPORTED_FILES_LOG = "imported_files.txt"

# Query IDs to pull (semicolon-separated in env, or default list)
DEFAULT_QUERY_IDS = ["1532356", "1532359"]


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


def _pull_from_ibkr(flex_client: FlexClient, data_dir: Path) -> list[Path]:
    """Pull Flex statements from IBKR and save as XML files.

    Returns:
        List of paths to saved XML files.
    """
    settings = get_settings()
    query_ids = DEFAULT_QUERY_IDS

    saved_files: list[Path] = []
    for query_id in query_ids:
        try:
            save_path = data_dir / f"ibkr_flex_{query_id}_latest.xml"
            flex_client.download_flex_statement(query_id, save_path)
            saved_files.append(save_path)
            logger.info("Pulled IBKR query %s -> %s", query_id, save_path)
        except FlexClientError as exc:
            logger.warning("Failed to pull IBKR query %s: %s", query_id, exc)

    return saved_files


def _import_xml_file(writer: SQLiteWriter, xml_path: Path) -> dict[str, int]:
    """Parse a Flex XML file and import into SQLite.

    Returns:
        Dict with counts of imported records per table.
    """
    results = parse_flex_xml(xml_path)
    counts: dict[str, int] = {"positions": 0, "trades": 0, "cash_flows": 0, "account_snapshots": 0}

    for result in results:
        if result.positions:
            n = writer.bulk_upsert_positions(result.positions)
            counts["positions"] += n

        if result.trades:
            for trade in result.trades:
                writer.insert_trade(trade)
            counts["trades"] += len(result.trades)

        if result.cash_flows:
            for cf in result.cash_flows:
                writer.insert_cash_flow(cf)
            counts["cash_flows"] += len(result.cash_flows)

        # Use parsed account snapshot if available, otherwise build from positions
        if result.account_snapshot:
            writer.upsert_account_snapshot(result.account_snapshot)
            counts["account_snapshots"] += 1
        elif result.positions:
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

    return counts


def run_daily_incremental_job() -> dict[str, dict[str, int]]:
    """Run the daily incremental import job.

    1. Pull fresh data from IBKR Flex Web Service (if configured)
    2. Scan data_dir for CSV files not yet imported
    3. Import each new file into SQLite

    Returns:
        A dict mapping source names to their import result dicts.
    """
    settings = get_settings()
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    writer = SQLiteWriter(settings.sqlite_path)
    writer.init_schema()
    all_results: dict[str, dict[str, int]] = {}

    # Step 1: Pull from IBKR if token is configured
    if settings.flex_token:
        logger.info("Pulling data from IBKR Flex Web Service...")
        flex_client = FlexClient(settings)
        xml_files = _pull_from_ibkr(flex_client, data_dir)

        for xml_path in xml_files:
            try:
                counts = _import_xml_file(writer, xml_path)
                all_results[f"ibkr:{xml_path.name}"] = counts
                _mark_imported(data_dir, xml_path.name)
                logger.info("Imported IBKR data from %s: %s", xml_path.name, counts)
            except Exception:
                logger.exception("Failed to import IBKR XML %s", xml_path)
    else:
        logger.info("FLEX_TOKEN not configured, skipping IBKR pull")

    # Step 2: Scan for CSV files
    imported_names = _get_imported_files(data_dir)
    csv_files = sorted(data_dir.glob("*.csv"))
    new_csv_count = 0

    for csv_file in csv_files:
        if csv_file.name in imported_names:
            continue

        logger.info("Processing new CSV file: %s", csv_file.name)
        try:
            counts = import_daily_snapshot_file(writer, csv_file)
            all_results[f"csv:{csv_file.name}"] = counts
            _mark_imported(data_dir, csv_file.name)
            new_csv_count += 1
        except Exception:
            logger.exception("Failed to import CSV %s", csv_file)

    logger.info(
        "Daily incremental job complete: %d IBKR sources, %d new CSV files",
        len([k for k in all_results if k.startswith("ibkr:")]),
        new_csv_count,
    )
    return all_results
