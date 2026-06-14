"""Market events sync job — periodic FOMC + BLS data refresh.

Imports the backend's market_event_service directly (shared PYTHONPATH
in the Docker merged container). Uses the backend's Database class to
access the shared SQLite database.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def run_market_events_sync() -> None:
    """Sync market events from external sources (Fed FOMC, BLS API).

    Reads config at runtime so admin UI changes take effect immediately.
    """
    from worker.core.config import get_settings
    from app.core.database import Database
    from app.services.market_event_service import sync_market_events

    settings = get_settings()
    db = Database(settings.sqlite_path)

    logger.info("Syncing market events...")
    try:
        results = sync_market_events(db, bls_api_key=settings.bls_api_key or None)
        total = sum(results.values())
        logger.info("Market events sync complete: %d events (%s)", total, results)
    except Exception as exc:
        logger.error("Market events sync failed: %s", exc)
