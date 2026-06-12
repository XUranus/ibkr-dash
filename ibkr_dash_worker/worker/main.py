"""CLI entry point for the IBKR Dash worker.

Usage:
    python -m worker.main fetch              # Pull data from IBKR, archive by date
    python -m worker.main import <file>      # Import a single file (auto-detect format)
    python -m worker.main import-all         # Import all unprocessed archived files
    python -m worker.main run                # fetch + import-all (full pipeline)
    python -m worker.main run-scheduler      # Run on a cron schedule
    python -m worker.main init-db            # Initialize database schema
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from worker.clients.sqlite_writer import SQLiteWriter
from worker.core.config import get_settings
from worker.core.logger import setup_logging

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="IBKR Dash worker — ETL from IBKR Flex reports to SQLite"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # fetch
    subparsers.add_parser(
        "fetch",
        help="Pull data from IBKR Flex Web Service and archive by date.",
    )

    # import <file>
    import_cmd = subparsers.add_parser(
        "import",
        help="Import a single Flex file (XML/CSV/TXT) into SQLite.",
    )
    import_cmd.add_argument(
        "file",
        help="Path to a Flex file.",
    )

    # import-all
    subparsers.add_parser(
        "import-all",
        help="Import all unprocessed archived files from data_dir.",
    )

    # run
    subparsers.add_parser(
        "run",
        help="Full pipeline: fetch from IBKR + import all archived files.",
    )

    # run-scheduler
    subparsers.add_parser(
        "run-scheduler",
        help="Run the background scheduler (daily fetch + import).",
    )

    # init-db
    subparsers.add_parser(
        "init-db",
        help="Initialize the SQLite database schema.",
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

    if args.command == "fetch":
        from worker.jobs.fetch_job import fetch_flex_statements
        files = fetch_flex_statements()
        logger.info("Fetched %d files", len(files))
        return

    if args.command == "import":
        file_path = _require_file(args.file)
        from worker.jobs.import_job import import_flex_file
        counts = import_flex_file(writer, file_path)
        logger.info("Import result: %s", counts)
        return

    if args.command == "import-all":
        from worker.jobs.import_job import import_all_archived
        results = import_all_archived()
        for name, counts in results.items():
            logger.info("%s -> %s", name, counts)
        return

    if args.command == "run":
        from worker.jobs.fetch_job import fetch_flex_statements
        from worker.jobs.import_job import import_all_archived

        # Step 1: Fetch from IBKR
        logger.info("Step 1: Fetching from IBKR...")
        files = fetch_flex_statements()
        logger.info("Fetched %d files", len(files))

        # Step 2: Import all archived files
        logger.info("Step 2: Importing archived files...")
        results = import_all_archived()
        for name, counts in results.items():
            logger.info("%s -> %s", name, counts)

        if not results:
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
