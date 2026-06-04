"""CLI entry point for the IBKR Dash worker.

Usage:
    python -m worker.main import <file>
    python -m worker.main run-scheduler
    python -m worker.main init-db
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from worker.clients.sqlite_writer import SQLiteWriter
from worker.core.config import get_settings
from worker.core.logger import setup_logging
from worker.jobs.daily_incremental_job import run_daily_incremental_job
from worker.jobs.import_daily_snapshot import import_daily_snapshot_file

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="IBKR Dash worker -- ETL from IBKR Flex CSV reports to SQLite"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # import <file>
    import_cmd = subparsers.add_parser(
        "import",
        help="Import a single Flex CSV file into SQLite.",
    )
    import_cmd.add_argument(
        "file",
        help="Path to a Flex CSV file.",
    )

    # run-scheduler
    subparsers.add_parser(
        "run-scheduler",
        help="Run the background scheduler. Scans data_dir for new CSV files on a cron schedule.",
    )

    # init-db
    subparsers.add_parser(
        "init-db",
        help="Initialize the SQLite database schema (create tables and indexes).",
    )

    # scan
    subparsers.add_parser(
        "scan",
        help="One-shot scan of data_dir for new CSV files and import them.",
    )

    return parser


def _require_file(file_path: str) -> Path:
    """Validate that a file path exists and return it as a Path."""
    candidate = Path(file_path)
    if not candidate.is_file():
        logger.error("File does not exist: %s", candidate)
        raise SystemExit(1)
    return candidate


def main() -> None:
    """Main CLI entry point."""
    settings = get_settings()
    setup_logging(settings.log_level)
    args = build_parser().parse_args()
    writer = SQLiteWriter(settings.sqlite_path)

    if args.command == "init-db":
        writer.init_schema()
        logger.info("Database schema initialized at %s", settings.sqlite_path)
        return

    if args.command == "import":
        file_path = _require_file(args.file)
        counts = import_daily_snapshot_file(writer, file_path)
        logger.info("Import result: %s", counts)
        return

    if args.command == "scan":
        results = run_daily_incremental_job()
        if results:
            for name, counts in results.items():
                logger.info("%s -> %s", name, counts)
        else:
            logger.info("No new files to import")
        return

    if args.command == "run-scheduler":
        from worker.core.scheduler import create_scheduler
        scheduler = create_scheduler()
        logger.info(
            "Starting scheduler (hour=%d, minute=%d, tz=%s)",
            settings.scheduler_hour,
            settings.scheduler_minute,
            settings.scheduler_timezone,
        )
        scheduler.start()

        # Keep the main thread alive while the scheduler runs in background
        try:
            import time
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down scheduler")
            scheduler.shutdown(wait=False)
        return


if __name__ == "__main__":
    main()
