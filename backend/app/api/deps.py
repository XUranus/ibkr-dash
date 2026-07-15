"""FastAPI dependency injection helpers.

Provides singleton database, settings, service providers,
and optional basic-auth dependencies.
"""

from __future__ import annotations

import hashlib
import logging
import secrets

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.auth import SESSION_COOKIE_NAME, verify_session_token
from app.core.config import Settings, get_settings
from app.core.database import Database, get_database

logger = logging.getLogger(__name__)

security = HTTPBasic(auto_error=False)


# ---------------------------------------------------------------------------
# Core dependencies
# ---------------------------------------------------------------------------


def get_db() -> Database:
    """Return the singleton Database instance."""
    db = get_database()
    # Check if data has changed (cheap single-row query, invalidates cache if needed)
    try:
        from app.core.cache import check_data_freshness
        check_data_freshness(db)
    except Exception:
        logger.debug("Cache freshness check failed (non-critical)", exc_info=True)
    return db


def get_app_settings() -> Settings:
    """Return the cached application settings."""
    return get_settings()


# ---------------------------------------------------------------------------
# Service providers (DI)
# ---------------------------------------------------------------------------


def get_account_service(db: Database = Depends(get_db)) -> "AccountService":
    """Provide an AccountService instance."""
    from app.services.account_service import AccountService
    return AccountService(db)


def get_position_service(db: Database = Depends(get_db)) -> "PositionService":
    """Provide a PositionService instance."""
    from app.services.position_service import PositionService
    return PositionService(db)


def get_trade_service(db: Database = Depends(get_db)) -> "TradeService":
    """Provide a TradeService instance."""
    from app.services.trade_service import TradeService
    return TradeService(db)


def get_cash_flow_service(db: Database = Depends(get_db)) -> "CashFlowService":
    """Provide a CashFlowService instance."""
    from app.services.cash_flow_service import CashFlowService
    return CashFlowService(db)


def get_dividend_service(db: Database = Depends(get_db)) -> "DividendService":
    """Provide a DividendService instance."""
    from app.services.dividend_service import DividendService
    return DividendService(db)


def get_chart_service(db: Database = Depends(get_db)) -> "ChartService":
    """Provide a ChartService instance."""
    from app.services.chart_service import ChartService
    return ChartService(db)


def get_llm_service(settings: Settings = Depends(get_app_settings)) -> "LLMService":
    """Provide an LLMService instance.

    Creates a fresh instance each time so that config changes (via admin UI)
    take effect immediately on the next request.
    """
    from app.services.llm_service import LLMService
    return LLMService(settings)


def get_agent_task_service(db: Database = Depends(get_db)) -> "AgentTaskService":
    """Provide an AgentTaskService instance."""
    from app.services.agent_services import AgentTaskService
    return AgentTaskService(db)


def get_prompt_service(db: Database = Depends(get_db)) -> "PromptService":
    """Provide a PromptService instance."""
    from app.services.prompt_service import PromptService
    return PromptService(db)


def get_investment_policy_service(db: Database = Depends(get_db)) -> "InvestmentPolicyService":
    """Provide an InvestmentPolicyService instance."""
    from app.services.investment_policy_service import InvestmentPolicyService
    return InvestmentPolicyService(db)


def get_llm_call_metrics_service(db: Database = Depends(get_db)) -> "LLMCallMetricsService":
    """Provide an LLMCallMetricsService instance."""
    from app.services.llm_call_metrics_service import LLMCallMetricsService
    return LLMCallMetricsService(db)


def get_es_client() -> "ElasticsearchClient":
    """Provide an ElasticsearchClient (SQLite-backed shim) instance."""
    from app.clients.es_client import ElasticsearchClient
    return ElasticsearchClient()


def get_agent_run_trace_service(db: Database = Depends(get_db)) -> "AgentRunTraceService":
    """Provide an AgentRunTraceService instance."""
    from app.services.agent_run_trace_service import AgentRunTraceService
    from app.services.agent_run_trace_repository import AgentRunTraceRepository
    return AgentRunTraceService(AgentRunTraceRepository(get_es_client(), get_settings()))


def get_agent_replay_service(db: Database = Depends(get_db)) -> "AgentReplayService":
    """Provide an AgentReplayService instance."""
    from app.services.agent_replay_service import AgentReplayService
    return AgentReplayService(db)


def get_agent_eval_service(db: Database = Depends(get_db)) -> "AgentEvalService":
    """Provide an AgentEvalService instance."""
    from app.services.agent_eval_repository import EvalCaseRepository, EvalRunRepository, BadCaseFeedbackRepository
    from app.core.database import Database as DB
    eval_db = DB(get_settings().sqlite_path)
    return {
        "case_repo": EvalCaseRepository(eval_db),
        "run_repo": EvalRunRepository(eval_db),
        "feedback_repo": BadCaseFeedbackRepository(eval_db),
    }


def require_admin_session(request: Request) -> str | None:
    """Require an admin session (alias for get_current_user)."""
    return get_current_user(request, None, get_settings())


def get_eval_simulation_service(db: Database = Depends(get_db)):
    from app.services.eval_simulation_repository import SyntheticSimulationRepository
    from app.services.eval_simulation_service import EvalSimulationService
    return EvalSimulationService(db)


def get_eval_failure_mining_service(db: Database = Depends(get_db)):
    from app.services.eval_failure_mining_repository import SyntheticFailureMiningRepository
    from app.services.eval_failure_mining_service import SyntheticFailureMiningService
    from app.services.eval_simulation_repository import SyntheticSimulationRepository
    return SyntheticFailureMiningService(
        failure_repository=SyntheticFailureMiningRepository(db),
        simulation_repository=SyntheticSimulationRepository(db),
    )


def get_failure_to_eval_case_service(db: Database = Depends(get_db)):
    from app.services.eval_failure_to_case_service import FailureToEvalCaseService
    return FailureToEvalCaseService(db)


def get_judge_calibration_service(db: Database = Depends(get_db)):
    from app.services.eval_failure_mining_repository import SyntheticFailureMiningRepository
    from app.services.eval_judge_calibration_repository import JudgeCalibrationRepository
    from app.services.eval_judge_calibration_service import JudgeCalibrationService
    from app.services.eval_simulation_repository import SyntheticSimulationRepository
    return JudgeCalibrationService(
        calibration_repository=JudgeCalibrationRepository(db),
        failure_repository=SyntheticFailureMiningRepository(db),
        simulation_repository=SyntheticSimulationRepository(db),
    )


def get_baseline_health_report_service(db: Database = Depends(get_db)):
    from app.services.eval_baseline_health_repository import BaselineHealthReportRepository
    from app.services.eval_baseline_health_service import BaselineHealthReportService
    from app.services.eval_failure_mining_repository import SyntheticFailureMiningRepository
    from app.services.eval_simulation_repository import SyntheticSimulationRepository
    return BaselineHealthReportService(
        report_repository=BaselineHealthReportRepository(db),
        simulation_repository=SyntheticSimulationRepository(db),
        failure_repository=SyntheticFailureMiningRepository(db),
    )


def get_longbridge_oauth_token_service():
    from app.services.longbridge_oauth_token_service import LongbridgeOAuthTokenService
    return LongbridgeOAuthTokenService(settings=get_settings())


def get_longbridge_openapi_oauth_service():
    from app.services.longbridge_openapi_oauth import LongbridgeOpenAPIOAuthService
    return LongbridgeOpenAPIOAuthService(settings=get_settings())


def get_longbridge_external_data_client():
    from app.services.longbridge_service import LongbridgeExternalDataClient
    return LongbridgeExternalDataClient(settings=get_settings())


def get_agent_regression_gate_service(db: Database = Depends(get_db)):
    from app.services.agent_regression_gate_service import RegressionGateService
    return RegressionGateService(db)


def get_agent_regression_profile_service(db: Database = Depends(get_db)):
    from app.services.agent_regression_profile_service import RegressionProfileService
    return RegressionProfileService(db)


def get_agent_change_impact_service(db: Database = Depends(get_db)):
    from app.services.agent_change_impact_service import AgentChangeImpactService
    return AgentChangeImpactService(db)


# ---------------------------------------------------------------------------
# Portfolio Manager domain services
# ---------------------------------------------------------------------------


def get_portfolio_constitution_service(db: Database = Depends(get_db)):
    from app.domains.portfolio_manager.constitution.repository import PortfolioConstitutionRepository
    from app.domains.portfolio_manager.constitution.service import PortfolioConstitutionService
    return PortfolioConstitutionService(PortfolioConstitutionRepository(db))


def get_portfolio_universe_service(db: Database = Depends(get_db)):
    from app.domains.portfolio_manager.universe.repository import PortfolioUniverseRepository
    from app.domains.portfolio_manager.universe.service import PortfolioUniverseService
    from app.services.position_service import PositionService
    return PortfolioUniverseService(PortfolioUniverseRepository(db), PositionService(db))


def _build_pm_services(db: Database, llm_service=None):
    """Build the full PM dependency graph. Returns a dict of all services."""
    from app.domains.portfolio_manager.constitution.repository import PortfolioConstitutionRepository
    from app.domains.portfolio_manager.constitution.service import PortfolioConstitutionService
    from app.domains.portfolio_manager.universe.repository import PortfolioUniverseRepository
    from app.domains.portfolio_manager.universe.service import PortfolioUniverseService
    from app.domains.portfolio_manager.watchtower.repository import PortfolioWatchtowerRepository
    from app.domains.portfolio_manager.watchtower.scanner import PortfolioWatchtowerScanner, WatchtowerPriceHistoryProvider
    from app.domains.portfolio_manager.watchtower.service import PortfolioWatchtowerService
    from app.domains.portfolio_manager.decision_orchestrator.repository import PortfolioAutoDecisionRepository
    from app.domains.portfolio_manager.decision_orchestrator.service import PortfolioAutoDecisionService
    from app.domains.portfolio_manager.decision_orchestrator.trigger_selector import PortfolioAutoDecisionTriggerSelector
    from app.domains.portfolio_manager.decision_orchestrator.runner import PortfolioAutoDecisionRunner
    from app.domains.portfolio_manager.evaluation.repository import PortfolioEvaluationRepository
    from app.domains.portfolio_manager.evaluation.service import PortfolioEvaluationService
    from app.domains.portfolio_manager.evaluation.outcome_evaluator import PortfolioAutoDecisionOutcomeEvaluator, PriceForwardReturnProvider
    from app.domains.portfolio_manager.evaluation.portfolio_replay import PortfolioReportEvaluator
    from app.domains.portfolio_manager.evaluation.watchtower_evaluator import PortfolioWatchtowerEvaluator
    from app.domains.portfolio_manager.improvement.repository import PortfolioImprovementRepository
    from app.domains.portfolio_manager.improvement.service import PortfolioImprovementService
    from app.domains.portfolio_manager.improvement.pattern_detector import PortfolioImprovementPatternDetector
    from app.domains.portfolio_manager.improvement.recommendation_builder import PortfolioImprovementRecommendationBuilder
    from app.domains.portfolio_manager.portfolio_review.repository import PortfolioReviewRepository
    from app.domains.portfolio_manager.portfolio_review.service import PortfolioReviewService
    from app.domains.portfolio_manager.portfolio_review.exposure_analyzer import PortfolioExposureAnalyzer
    from app.domains.portfolio_manager.portfolio_review.allocation_analyzer import PortfolioAllocationAnalyzer
    from app.domains.portfolio_manager.portfolio_review.report_composer import PortfolioReportComposer
    from app.services.position_service import PositionService
    from app.services.account_service import AccountService

    # Layer 0: repositories
    constitution_repo = PortfolioConstitutionRepository(db)
    universe_repo = PortfolioUniverseRepository(db)
    watchtower_repo = PortfolioWatchtowerRepository(db)
    auto_decision_repo = PortfolioAutoDecisionRepository(db)
    evaluation_repo = PortfolioEvaluationRepository(db)
    improvement_repo = PortfolioImprovementRepository(db)
    review_repo = PortfolioReviewRepository(db)
    position_service = PositionService(db)
    account_service = AccountService(db)

    # Layer 1: base services
    constitution_service = PortfolioConstitutionService(constitution_repo)
    universe_service = PortfolioUniverseService(universe_repo, position_service)

    # Layer 2: watchtower
    watchtower_service = PortfolioWatchtowerService(
        repository=watchtower_repo,
        universe_service=universe_service,
        constitution_service=constitution_service,
        position_service=position_service,
        scanner=PortfolioWatchtowerScanner(WatchtowerPriceHistoryProvider(db)),
    )

    # Layer 3: auto decision
    runner = None
    if llm_service is not None:
        from app.services.trade_decision_agent import TradeDecisionAgent
        from app.services.trade_decision_evidence import TradeDecisionEvidenceBuilder
        from app.services.trade_decision_repository import TradeDecisionRepository
        trade_agent = TradeDecisionAgent(
            evidence_builder=TradeDecisionEvidenceBuilder(db),
            llm_service=llm_service,
            repository=TradeDecisionRepository(db),
        )
        runner = PortfolioAutoDecisionRunner(trade_agent)

    auto_decision_service = PortfolioAutoDecisionService(
        repository=auto_decision_repo,
        watchtower_service=watchtower_service,
        constitution_service=constitution_service,
        universe_service=universe_service,
        trigger_selector=PortfolioAutoDecisionTriggerSelector(),
        runner=runner,
    )

    # Layer 4: evaluation, improvement, review
    evaluation_service = PortfolioEvaluationService(
        repository=evaluation_repo,
        watchtower_repository=watchtower_repo,
        auto_decision_repository=auto_decision_repo,
        portfolio_review_repository=review_repo,
        price_provider=PriceForwardReturnProvider(db),
        watchtower_evaluator=PortfolioWatchtowerEvaluator(),
        auto_decision_evaluator=PortfolioAutoDecisionOutcomeEvaluator(),
        portfolio_report_evaluator=PortfolioReportEvaluator(),
    )

    improvement_service = PortfolioImprovementService(
        repository=improvement_repo,
        evaluation_repository=evaluation_repo,
        pattern_detector=PortfolioImprovementPatternDetector(),
        recommendation_builder=PortfolioImprovementRecommendationBuilder(),
    )

    review_service = PortfolioReviewService(
        repository=review_repo,
        constitution_service=constitution_service,
        universe_service=universe_service,
        watchtower_service=watchtower_service,
        auto_decision_service=auto_decision_service,
        position_service=position_service,
        account_service=account_service,
        exposure_analyzer=PortfolioExposureAnalyzer(),
        allocation_analyzer=PortfolioAllocationAnalyzer(),
        report_composer=PortfolioReportComposer(),
    )

    return {
        "constitution_service": constitution_service,
        "universe_service": universe_service,
        "watchtower_service": watchtower_service,
        "auto_decision_service": auto_decision_service,
        "evaluation_service": evaluation_service,
        "improvement_service": improvement_service,
        "review_service": review_service,
    }


def get_portfolio_watchtower_service(db: Database = Depends(get_db)):
    return _build_pm_services(db)["watchtower_service"]


def get_portfolio_daily_loop_service(db: Database = Depends(get_db)):
    from app.domains.portfolio_manager.daily_loop.repository import PortfolioDailyLoopRepository
    from app.domains.portfolio_manager.daily_loop.service import PortfolioDailyLoopService
    from app.services.llm_service import LLMService
    settings = get_settings()
    llm_svc = LLMService(settings)
    services = _build_pm_services(db, llm_service=llm_svc)
    return PortfolioDailyLoopService(
        repository=PortfolioDailyLoopRepository(db),
        universe_service=services["universe_service"],
        watchtower_service=services["watchtower_service"],
        auto_decision_service=services["auto_decision_service"],
        portfolio_review_service=services["review_service"],
        evaluation_service=services["evaluation_service"],
        improvement_service=services["improvement_service"],
        llm_service=llm_svc,
        db=db,
    )


def get_portfolio_auto_decision_service(db: Database = Depends(get_db)):
    return _build_pm_services(db)["auto_decision_service"]


def get_portfolio_evaluation_service(db: Database = Depends(get_db)):
    return _build_pm_services(db)["evaluation_service"]


def get_portfolio_improvement_service(db: Database = Depends(get_db)):
    return _build_pm_services(db)["improvement_service"]


def get_portfolio_review_service(db: Database = Depends(get_db)):
    return _build_pm_services(db)["review_service"]


def get_portfolio_action_alert_service(db: Database = Depends(get_db)):
    from app.domains.portfolio_manager.action_alerts.repository import PortfolioActionAlertRepository
    from app.domains.portfolio_manager.action_alerts.service import PortfolioActionAlertService
    from app.domains.portfolio_manager.action_alerts.alert_builder import PortfolioActionAlertBuilder
    services = _build_pm_services(db)
    daily_loop_svc = get_portfolio_daily_loop_service(db)
    return PortfolioActionAlertService(
        repository=PortfolioActionAlertRepository(db),
        daily_loop_service=daily_loop_svc,
        auto_decision_service=services["auto_decision_service"],
        portfolio_review_service=services["review_service"],
        watchtower_service=services["watchtower_service"],
        builder=PortfolioActionAlertBuilder(),
    )


def get_agent_task_repository():
    from app.services.agent_task_repository import AgentTaskRepository
    return AgentTaskRepository(get_es_client(), get_settings())


def require_authenticated_session(request: Request) -> "AuthSession":
    """Require an authenticated session for Portfolio Manager routes."""
    import time
    from app.core.auth import AuthSession
    settings = get_settings()
    if not settings.auth_password:
        return AuthSession(username="anonymous", expires_at=int(time.time()) + 86400)
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        secret = hashlib.sha256(settings.auth_password.encode()).hexdigest()
        session = verify_session_token(session_token, secret=secret)
        if session:
            return session
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


# ---------------------------------------------------------------------------
# Optional basic auth
# ---------------------------------------------------------------------------


def get_current_user(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(security),
    settings: Settings = Depends(get_app_settings),
) -> str | None:
    """Validate authentication via session cookie or HTTP Basic credentials.

    When ``auth_password`` is not configured, anonymous access is allowed.
    Otherwise, the dependency first checks for a session cookie
    (``ibkr_dash_session``) and then falls back to HTTP Basic auth.
    Returns 401 WITHOUT ``WWW-Authenticate`` header to avoid browser dialog.
    """
    if not settings.auth_password:
        # Auth is not configured -- allow anonymous access.
        return None

    # Try session cookie first
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        secret = hashlib.sha256(settings.auth_password.encode()).hexdigest()
        session = verify_session_token(session_token, secret=secret)
        if session:
            return session.username

    # Fall back to HTTP Basic (for API clients like curl)
    if credentials:
        correct_username = secrets.compare_digest(credentials.username, settings.auth_username)
        correct_password = secrets.compare_digest(credentials.password, settings.auth_password)
        if correct_username and correct_password:
            return credentials.username

    # Return 401 WITHOUT WWW-Authenticate header to avoid browser dialog
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


def get_optional_user(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(security),
    settings: Settings = Depends(get_app_settings),
) -> str | None:
    """Like ``get_current_user`` but never raises — returns None if unauthenticated.

    Use for public-facing endpoints (dashboard, positions) that should
    work for everyone but still identify logged-in users.
    """
    if not settings.auth_password:
        return None

    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        secret = hashlib.sha256(settings.auth_password.encode()).hexdigest()
        session = verify_session_token(session_token, secret=secret)
        if session:
            return session.username

    if credentials:
        correct_username = secrets.compare_digest(credentials.username, settings.auth_username)
        correct_password = secrets.compare_digest(credentials.password, settings.auth_password)
        if correct_username and correct_password:
            return credentials.username

    return None
