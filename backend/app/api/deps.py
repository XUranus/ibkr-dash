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


def get_agent_run_trace_service(db: Database = Depends(get_db), es_client=Depends(get_es_client)) -> "AgentRunTraceService":
    """Provide an AgentRunTraceService instance."""
    from app.services.agent_run_trace_service import AgentRunTraceService
    return AgentRunTraceService(es_client, get_settings())


def get_agent_replay_service(db: Database = Depends(get_db), es_client=Depends(get_es_client)) -> "AgentReplayService":
    """Provide an AgentReplayService instance."""
    from app.services.agent_replay_service import AgentReplayService
    return AgentReplayService(es_client, get_settings())


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


def get_eval_simulation_service(db: Database = Depends(get_db)) -> "SyntheticSimulationService":
    from app.services.eval_simulation_service import SyntheticSimulationService
    return SyntheticSimulationService(db)


def get_eval_failure_mining_service(db: Database = Depends(get_db)) -> "SyntheticFailureMiningService":
    from app.services.eval_failure_mining_service import SyntheticFailureMiningService
    return SyntheticFailureMiningService(db)


def get_failure_to_eval_case_service(db: Database = Depends(get_db)):
    from app.services.eval_failure_to_case_service import FailureToEvalCaseService
    return FailureToEvalCaseService(db)


def get_judge_calibration_service(db: Database = Depends(get_db)):
    from app.services.eval_judge_calibration_service import JudgeCalibrationService
    return JudgeCalibrationService(db)


def get_baseline_health_report_service(db: Database = Depends(get_db)):
    from app.services.eval_baseline_health_service import BaselineHealthService
    return BaselineHealthService(db)


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


def get_portfolio_watchtower_service(db: Database = Depends(get_db)):
    from app.domains.portfolio_manager.watchtower.repository import PortfolioWatchtowerRepository
    from app.domains.portfolio_manager.watchtower.scanner import PortfolioWatchtowerScanner, WatchtowerPriceHistoryProvider
    from app.domains.portfolio_manager.watchtower.service import PortfolioWatchtowerService
    from app.domains.portfolio_manager.constitution.repository import PortfolioConstitutionRepository
    from app.domains.portfolio_manager.universe.repository import PortfolioUniverseRepository
    from app.services.position_service import PositionService
    from app.services.account_service import AccountService
    return PortfolioWatchtowerService(
        repository=PortfolioWatchtowerRepository(db),
        constitution_repository=PortfolioConstitutionRepository(db),
        universe_repository=PortfolioUniverseRepository(db),
        position_service=PositionService(db),
        account_service=AccountService(db),
        scanner=PortfolioWatchtowerScanner(WatchtowerPriceHistoryProvider(db)),
    )


def get_portfolio_daily_loop_service(db: Database = Depends(get_db)):
    from app.domains.portfolio_manager.daily_loop.repository import PortfolioDailyLoopRepository
    from app.domains.portfolio_manager.daily_loop.service import PortfolioDailyLoopService
    from app.domains.portfolio_manager.watchtower.repository import PortfolioWatchtowerRepository
    from app.domains.portfolio_manager.watchtower.scanner import PortfolioWatchtowerScanner, WatchtowerPriceHistoryProvider
    from app.domains.portfolio_manager.watchtower.service import PortfolioWatchtowerService
    from app.domains.portfolio_manager.constitution.repository import PortfolioConstitutionRepository
    from app.domains.portfolio_manager.universe.repository import PortfolioUniverseRepository
    from app.domains.portfolio_manager.decision_orchestrator.repository import PortfolioAutoDecisionRepository
    from app.domains.portfolio_manager.decision_orchestrator.service import PortfolioAutoDecisionService
    from app.domains.portfolio_manager.evaluation.repository import PortfolioEvaluationRepository
    from app.domains.portfolio_manager.evaluation.service import PortfolioEvaluationService
    from app.domains.portfolio_manager.improvement.repository import PortfolioImprovementRepository
    from app.domains.portfolio_manager.improvement.service import PortfolioImprovementService
    from app.domains.portfolio_manager.portfolio_review.repository import PortfolioReviewRepository
    from app.domains.portfolio_manager.portfolio_review.service import PortfolioReviewService
    from app.services.position_service import PositionService
    from app.services.account_service import AccountService
    from app.services.trade_service import TradeService
    return PortfolioDailyLoopService(
        repository=PortfolioDailyLoopRepository(db),
        watchtower_service=PortfolioWatchtowerService(
            repository=PortfolioWatchtowerRepository(db),
            constitution_repository=PortfolioConstitutionRepository(db),
            universe_repository=PortfolioUniverseRepository(db),
            position_service=PositionService(db),
            account_service=AccountService(db),
            scanner=PortfolioWatchtowerScanner(WatchtowerPriceHistoryProvider(db)),
        ),
        auto_decision_service=PortfolioAutoDecisionService(
            repository=PortfolioAutoDecisionRepository(db),
            watchtower_repository=PortfolioWatchtowerRepository(db),
            universe_repository=PortfolioUniverseRepository(db),
            constitution_repository=PortfolioConstitutionRepository(db),
            trade_decision_service=None,
        ),
        evaluation_service=PortfolioEvaluationService(
            repository=PortfolioEvaluationRepository(db),
            watchtower_repository=PortfolioWatchtowerRepository(db),
            auto_decision_repository=PortfolioAutoDecisionRepository(db),
            price_provider=None,
        ),
        improvement_service=PortfolioImprovementService(
            repository=PortfolioImprovementRepository(db),
            evaluation_repository=PortfolioEvaluationRepository(db),
        ),
        review_service=PortfolioReviewService(
            repository=PortfolioReviewRepository(db),
            constitution_repository=PortfolioConstitutionRepository(db),
            universe_repository=PortfolioUniverseRepository(db),
            watchtower_repository=PortfolioWatchtowerRepository(db),
            auto_decision_repository=PortfolioAutoDecisionRepository(db),
            position_service=PositionService(db),
            account_service=AccountService(db),
        ),
        universe_repository=PortfolioUniverseRepository(db),
        constitution_repository=PortfolioConstitutionRepository(db),
        trade_service=TradeService(db),
    )


def get_portfolio_auto_decision_service(db: Database = Depends(get_db)):
    from app.domains.portfolio_manager.decision_orchestrator.repository import PortfolioAutoDecisionRepository
    from app.domains.portfolio_manager.decision_orchestrator.service import PortfolioAutoDecisionService
    from app.domains.portfolio_manager.watchtower.repository import PortfolioWatchtowerRepository
    from app.domains.portfolio_manager.universe.repository import PortfolioUniverseRepository
    from app.domains.portfolio_manager.constitution.repository import PortfolioConstitutionRepository
    return PortfolioAutoDecisionService(
        repository=PortfolioAutoDecisionRepository(db),
        watchtower_repository=PortfolioWatchtowerRepository(db),
        universe_repository=PortfolioUniverseRepository(db),
        constitution_repository=PortfolioConstitutionRepository(db),
        trade_decision_service=None,
    )


def get_portfolio_evaluation_service(db: Database = Depends(get_db)):
    from app.domains.portfolio_manager.evaluation.repository import PortfolioEvaluationRepository
    from app.domains.portfolio_manager.evaluation.service import PortfolioEvaluationService
    from app.domains.portfolio_manager.watchtower.repository import PortfolioWatchtowerRepository
    from app.domains.portfolio_manager.decision_orchestrator.repository import PortfolioAutoDecisionRepository
    return PortfolioEvaluationService(
        repository=PortfolioEvaluationRepository(db),
        watchtower_repository=PortfolioWatchtowerRepository(db),
        auto_decision_repository=PortfolioAutoDecisionRepository(db),
        price_provider=None,
    )


def get_portfolio_improvement_service(db: Database = Depends(get_db)):
    from app.domains.portfolio_manager.improvement.repository import PortfolioImprovementRepository
    from app.domains.portfolio_manager.improvement.service import PortfolioImprovementService
    from app.domains.portfolio_manager.evaluation.repository import PortfolioEvaluationRepository
    return PortfolioImprovementService(
        repository=PortfolioImprovementRepository(db),
        evaluation_repository=PortfolioEvaluationRepository(db),
    )


def get_portfolio_review_service(db: Database = Depends(get_db)):
    from app.domains.portfolio_manager.portfolio_review.repository import PortfolioReviewRepository
    from app.domains.portfolio_manager.portfolio_review.service import PortfolioReviewService
    from app.domains.portfolio_manager.constitution.repository import PortfolioConstitutionRepository
    from app.domains.portfolio_manager.universe.repository import PortfolioUniverseRepository
    from app.domains.portfolio_manager.watchtower.repository import PortfolioWatchtowerRepository
    from app.domains.portfolio_manager.decision_orchestrator.repository import PortfolioAutoDecisionRepository
    from app.services.position_service import PositionService
    from app.services.account_service import AccountService
    return PortfolioReviewService(
        repository=PortfolioReviewRepository(db),
        constitution_repository=PortfolioConstitutionRepository(db),
        universe_repository=PortfolioUniverseRepository(db),
        watchtower_repository=PortfolioWatchtowerRepository(db),
        auto_decision_repository=PortfolioAutoDecisionRepository(db),
        position_service=PositionService(db),
        account_service=AccountService(db),
    )


def get_portfolio_action_alert_service(db: Database = Depends(get_db)):
    from app.domains.portfolio_manager.action_alerts.repository import PortfolioActionAlertRepository
    from app.domains.portfolio_manager.action_alerts.service import PortfolioActionAlertService
    from app.domains.portfolio_manager.daily_loop.repository import PortfolioDailyLoopRepository
    from app.domains.portfolio_manager.decision_orchestrator.repository import PortfolioAutoDecisionRepository
    from app.services.email_service import EmailService
    return PortfolioActionAlertService(
        repository=PortfolioActionAlertRepository(db),
        daily_loop_repository=PortfolioDailyLoopRepository(db),
        auto_decision_repository=PortfolioAutoDecisionRepository(db),
        email_service=EmailService(get_settings()),
    )


def get_agent_task_repository(db: Database = Depends(get_db)):
    from app.services.agent_task_repository import AgentTaskRepository
    return AgentTaskRepository(db)


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
