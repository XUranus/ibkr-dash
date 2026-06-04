"""Daily incremental import job.

Scans the configured data_dir for Flex CSV files that have not yet been
imported and processes each one.  Tracks imported files by name in a
simple text file alongside the data directory.
"""

from __future__ import annotations

import logging
from pathlib import Path

from worker.clients.sqlite_writer import SQLiteWriter
from worker.core.config import get_settings
from worker.jobs.import_daily_snapshot import import_daily_snapshot_file

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


def run_daily_incremental_job() -> dict[str, dict[str, int]]:
    """Scan data_dir for new CSV files and import each one.

    Returns:
        A dict mapping file names to their import result dicts.
    """
    settings = get_settings()
    data_dir = Path(settings.data_dir)

    if not data_dir.is_dir():
        logger.warning("Data directory does not exist: %s", data_dir)
        return {}

    writer = SQLiteWriter(settings.sqlite_path)
    imported_names = _get_imported_files(data_dir)
    csv_files = sorted(data_dir.glob("*.csv"))

    if not csv_files:
        logger.info("No CSV files found in %s", data_dir)
        return {}

    results: dict[str, dict[str, int]] = {}
    new_file_count = 0

    for csv_file in csv_files:
        if csv_file.name in imported_names:
            logger.debug("Skipping already-imported file: %s", csv_file.name)
            continue

        logger.info("Processing new file: %s", csv_file.name)
        try:
            counts = import_daily_snapshot_file(writer, csv_file)
            _mark_imported(data_dir, csv_file.name)
            results[csv_file.name] = counts
            new_file_count += 1
        except Exception:
            logger.exception("Failed to import %s", csv_file.name)
            continue

    logger.info(
        "Daily incremental job complete: %d new file(s) imported out of %d total",
        new_file_count,
        len(csv_files),
    )
    return results
