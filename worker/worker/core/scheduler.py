"""APScheduler-based scheduler for periodic worker jobs."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler

from worker.core.config import get_settings
from worker.jobs.daily_incremental_job import run_daily_incremental_job


def create_scheduler() -> BackgroundScheduler:
    """Create and configure a background scheduler with the daily incremental job.

    The job schedule is controlled by settings (scheduler_hour, scheduler_minute,
    scheduler_timezone).
    """
    settings = get_settings()
    tz = ZoneInfo(settings.scheduler_timezone)

    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(
        run_daily_incremental_job,
        trigger="cron",
        hour=settings.scheduler_hour,
        minute=settings.scheduler_minute,
        id="daily_incremental_job",
        replace_existing=True,
    )
    return scheduler
