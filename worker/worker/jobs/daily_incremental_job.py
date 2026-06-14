"""Daily incremental import job — backward-compatible wrapper.

This module delegates to fetch_job and import_job.
New code should use those modules directly.
"""

from __future__ import annotations

import logging

from worker.jobs.fetch_job import fetch_flex_statements
from worker.jobs.import_job import import_all_archived

logger = logging.getLogger(__name__)


def run_daily_incremental_job() -> dict[str, dict[str, int]]:
    """Run the daily incremental import job.

    1. Pull fresh data from IBKR Flex Web Service (if configured)
    2. Scan data_dir for all unprocessed files
    3. Import each new file into SQLite

    Returns:
        A dict mapping source names to their import result dicts.
    """
    # Step 1: Fetch from IBKR
    logger.info("Pulling data from IBKR Flex Web Service...")
    fetch_flex_statements()

    # Step 2: Import all archived files
    results = import_all_archived()

    # Format output for backward compatibility
    all_results: dict[str, dict[str, int]] = {}
    for name, counts in results.items():
        if name.endswith(".xml"):
            all_results[f"ibkr:{name}"] = counts
        elif name.endswith(".csv"):
            all_results[f"csv:{name}"] = counts
        else:
            all_results[name] = counts

    logger.info(
        "Daily incremental job complete: %d files imported",
        len(all_results),
    )
    return all_results
