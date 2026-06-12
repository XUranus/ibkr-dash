"""Fetch job: pull data from IBKR Flex Web Service and archive by date.

This module handles ONLY the network I/O — no parsing, no database writes.
Downloaded files are saved with date-based naming for archival:
    data/flex_exports/{query_id}_{YYYY-MM-DD}.xml

If the file for today already exists, the fetch is skipped.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from worker.clients.flex_client import FlexClient, FlexClientError
from worker.core.config import get_settings

logger = logging.getLogger(__name__)

# Default query IDs to pull
DEFAULT_QUERY_IDS = ["1532356", "1532359"]


def fetch_flex_statements(
    data_dir: Path | str | None = None,
    query_ids: list[str] | None = None,
) -> list[Path]:
    """Pull Flex statements from IBKR and archive by date.

    For each query_id, saves as {query_id}_{YYYY-MM-DD}.xml.
    If today's file already exists, skips the pull.

    Args:
        data_dir: Directory to save files. Defaults to settings.data_dir.
        query_ids: Query IDs to pull. Defaults to DEFAULT_QUERY_IDS.

    Returns:
        List of paths to fetched (or already-existing) files.
    """
    settings = get_settings()
    data_dir = Path(data_dir or settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    if not settings.flex_token:
        logger.warning("FLEX_TOKEN not configured, skipping fetch")
        return []

    query_ids = query_ids or DEFAULT_QUERY_IDS
    today = date.today().isoformat()  # YYYY-MM-DD
    flex_client = FlexClient(settings)

    saved_files: list[Path] = []
    for query_id in query_ids:
        save_path = data_dir / f"{query_id}_{today}.xml"

        if save_path.exists():
            logger.info("Already fetched today: %s", save_path.name)
            saved_files.append(save_path)
            continue

        try:
            flex_client.download_flex_statement(query_id, save_path)
            saved_files.append(save_path)
            logger.info("Fetched IBKR query %s -> %s", query_id, save_path.name)
        except FlexClientError as exc:
            logger.warning("Failed to fetch IBKR query %s: %s", query_id, exc)

    return saved_files
