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
        pass  # don't break the request if cache check fails
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
