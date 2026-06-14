"""Daily snapshot import pipeline.

Parses a Flex CSV file, transforms the data, and writes it to SQLite.
This is the main entry point for importing daily IBKR data.
"""

from __future__ import annotations

import logging
from pathlib import Path

from worker.core.config import Settings
from worker.parsers.flex_csv_parser import parse_flex_csv
from worker.parsers.transformers import transform_daily_statement
from worker.writers.sqlite_writer import SqliteWriter

logger = logging.getLogger(__name__)


class DailySnapshotImporter:
    """Imports a daily Flex CSV snapshot into the SQLite database.

    The pipeline: parse CSV -> transform -> write to SQLite.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def import_file(self, csv_path: str | Path) -> dict[str, int]:
        """Import a single Flex CSV file into the database.

        Args:
            csv_path: Path to the Flex CSV file.

        Returns:
            A dict with counts of records written per entity type.
        """
        source = Path(csv_path)
        logger.info("starting daily snapshot import from %s", source)

        # Step 1: Parse the Flex CSV
        statement = parse_flex_csv(source)
        logger.info(
            "parsed %s: %d sections, accounts=%s",
            source.name,
            len(statement.sections),
            statement.metadata.account_ids,
        )

        # Step 2: Transform into SQLite-ready dicts
        result = transform_daily_statement(statement)
        logger.info(
            "transformed: accounts=%d, positions=%d, trades=%d, cash_flows=%d, price_history=%d",
            len(result.account_documents),
            len(result.position_documents),
            len(result.trade_documents),
            len(result.cash_flow_documents),
            len(result.price_history_documents),
        )

        # Step 3: Write to SQLite
        writer = SqliteWriter(self.settings.sqlite_path)
        writer.init_schema()
        counts = writer.write_transform_result(result)
        logger.info("daily snapshot import complete: %s", counts)

        return counts

    def import_latest(self) -> dict[str, int] | None:
        """Import the latest Flex CSV file from the data directory.

        Looks for CSV files in the configured data_dir and imports
        the most recently modified one.

        Returns:
            A dict with counts of records written, or None if no files found.
        """
        data_dir = Path(self.settings.data_dir)
        if not data_dir.exists():
            logger.warning("data directory does not exist: %s", data_dir)
            return None

        csv_files = sorted(
            data_dir.glob("*.csv"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not csv_files:
            logger.warning("no CSV files found in %s", data_dir)
            return None

        latest = csv_files[0]
        logger.info("found latest CSV: %s", latest)
        return self.import_file(latest)
