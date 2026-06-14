"""APScheduler-based scheduler for periodic worker jobs."""

from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler

from worker.core.config import get_settings
from worker.jobs.daily_incremental_job import run_daily_incremental_job
from worker.jobs.market_events_sync_job import run_market_events_sync

logger = logging.getLogger(__name__)


def create_scheduler() -> BackgroundScheduler:
    """Create and configure a background scheduler with all periodic jobs.

    Jobs:
    1. Daily incremental import (IBKR data fetch + import)
    2. Market events sync (FOMC + BLS, configurable interval)

    Schedule settings are read at scheduler creation time.
    Market events sync interval is configurable via
    scheduler.market_events_sync_interval_hours in config.json.
    """
    settings = get_settings()
    tz = ZoneInfo(settings.scheduler_timezone)

    scheduler = BackgroundScheduler(timezone=tz)

    # Job 1: Daily incremental import
    scheduler.add_job(
        run_daily_incremental_job,
        trigger="cron",
        hour=settings.scheduler_hour,
        minute=settings.scheduler_minute,
        id="daily_incremental_job",
        replace_existing=True,
    )

    # Job 2: Market events sync (configurable interval)
    sync_hours = settings.market_events_sync_interval_hours
    scheduler.add_job(
        run_market_events_sync,
        trigger="interval",
        hours=sync_hours,
        id="market_events_sync",
        replace_existing=True,
    )
    logger.info(
        "Market events sync scheduled every %d hours",
        sync_hours,
    )

    return scheduler
