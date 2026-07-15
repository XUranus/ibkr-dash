"""Background scheduler for portfolio daily loop.

Triggers the daily loop at the configured time each day.
Uses APScheduler (already a backend dependency).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_scheduler: Any = None


def start_portfolio_scheduler() -> None:
    """Start the portfolio daily loop scheduler if enabled."""
    global _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from app.core.config import get_settings
        settings = get_settings()

        if not settings.portfolio_daily_loop_schedule_enabled:
            logger.info("Portfolio daily loop scheduler: disabled")
            return

        time_str = settings.portfolio_daily_loop_schedule_time  # e.g. "16:30"
        tz_name = settings.portfolio_daily_loop_schedule_timezone  # e.g. "America/New_York"

        parts = time_str.split(":", 1)
        if len(parts) != 2:
            logger.warning("Portfolio scheduler: invalid schedule_time=%s, skipping", time_str)
            return
        hour, minute = int(parts[0]), int(parts[1])

        scheduler = BackgroundScheduler(timezone=tz_name)
        scheduler.add_job(
            _run_daily_loop,
            trigger="cron",
            hour=hour,
            minute=minute,
            id="portfolio_daily_loop",
            replace_existing=True,
            kwargs={"settings": settings},
        )
        scheduler.start()
        _scheduler = scheduler
        logger.info("Portfolio daily loop scheduler: started, daily at %s %s", time_str, tz_name)
    except Exception:
        logger.exception("Portfolio daily loop scheduler: failed to start")


def stop_portfolio_scheduler() -> None:
    """Stop the scheduler on shutdown."""
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
            logger.info("Portfolio daily loop scheduler: stopped")
        except Exception:
            logger.debug("Portfolio scheduler shutdown error", exc_info=True)
        _scheduler = None


def _run_daily_loop(settings: Any) -> None:
    """Execute the scheduled daily loop run."""
    try:
        from app.core.database import Database
        from app.services.llm_service import LLMService
        from app.domains.portfolio_manager.daily_loop.repository import PortfolioDailyLoopRepository
        from app.domains.portfolio_manager.daily_loop.schedule import (
            find_existing_scheduled_run,
            scheduled_metadata,
            scheduled_options,
            today_in_timezone,
        )
        from app.domains.portfolio_manager.daily_loop.service import PortfolioDailyLoopService
        from app.api.deps import _build_pm_services

        tz_name = settings.portfolio_daily_loop_schedule_timezone
        effective_date = today_in_timezone(tz_name)
        logger.info("Portfolio daily loop scheduler: triggered for date=%s", effective_date)

        # Check for existing scheduled run today
        db = Database(settings.sqlite_path)
        repository = PortfolioDailyLoopRepository(db)
        existing = find_existing_scheduled_run(repository, run_date=effective_date)
        if existing:
            logger.info("Portfolio daily loop scheduler: already ran today (run_id=%s), skipping", existing.get("id"))
            return

        # Build services
        llm_service = LLMService(settings)
        pm_services = _build_pm_services(db)

        # Set up auto decision runner with LLM
        auto_decision_svc = pm_services["auto_decision_service"]
        if auto_decision_svc.runner is None and llm_service.api_key:
            try:
                from app.services.trade_decision_agent import TradeDecisionAgent
                from app.services.trade_decision_evidence import TradeDecisionEvidenceBuilder
                from app.services.trade_decision_repository import TradeDecisionRepository
                from app.domains.portfolio_manager.decision_orchestrator.runner import PortfolioAutoDecisionRunner
                from app.services.longbridge_service import LongbridgeExternalDataClient
                from app.clients.es_client import ElasticsearchClient
                lb_client = LongbridgeExternalDataClient(settings)
                es_client = ElasticsearchClient(settings)
                trade_agent = TradeDecisionAgent(
                    evidence_builder=TradeDecisionEvidenceBuilder(es_client, settings, lb_client),
                    llm_service=llm_service,
                    repository=TradeDecisionRepository(es_client, settings),
                )
                auto_decision_svc.runner = PortfolioAutoDecisionRunner(trade_agent)
            except Exception:
                logger.debug("Auto decision runner init skipped", exc_info=True)

        svc = PortfolioDailyLoopService(
            repository=repository,
            universe_service=pm_services["universe_service"],
            watchtower_service=pm_services["watchtower_service"],
            auto_decision_service=auto_decision_svc,
            portfolio_review_service=pm_services["review_service"],
            evaluation_service=pm_services["evaluation_service"],
            improvement_service=pm_services["improvement_service"],
            llm_service=llm_service,
            db=db,
        )

        options = scheduled_options(settings)
        run = svc.run_daily_loop(
            run_date=effective_date,
            run_type="scheduled",
            run_metadata=scheduled_metadata(settings, triggered_by="scheduler"),
            **options.model_dump(),
        )
        logger.info("Portfolio daily loop scheduler: completed, run_id=%s status=%s", run.id, run.status)

        # Trigger action alerts
        try:
            from app.domains.portfolio_manager.action_alerts.service import PortfolioActionAlertService
            from app.domains.portfolio_manager.action_alerts.repository import PortfolioActionAlertRepository
            from app.domains.portfolio_manager.action_alerts.alert_builder import PortfolioActionAlertBuilder
            from app.domains.portfolio_manager.daily_loop.runner import run_action_alerts_for_daily_loop
            action_alert_svc = PortfolioActionAlertService(
                repository=PortfolioActionAlertRepository(db),
                daily_loop_service=svc,
                auto_decision_service=pm_services["auto_decision_service"],
                portfolio_review_service=pm_services["review_service"],
                watchtower_service=pm_services["watchtower_service"],
                builder=PortfolioActionAlertBuilder(),
            )
            run_action_alerts_for_daily_loop(run, svc, action_alert_svc)
        except Exception:
            logger.debug("Portfolio scheduler: action alerts failed", exc_info=True)

    except Exception:
        logger.exception("Portfolio daily loop scheduler: run failed")
