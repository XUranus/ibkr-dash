"""FastAPI dependency injection helpers.

Provides singleton database, settings, service providers,
and optional basic-auth dependencies.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from functools import lru_cache

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
    return get_database()


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


@lru_cache(maxsize=1)
def _cached_llm_service(settings_hash: str, base_url: str, api_key: str) -> "LLMService":
    """Return a process-wide singleton LLMService.

    The ``settings_hash`` parameter exists solely to make ``lru_cache``
    invalidate correctly when the underlying settings change (unlikely
    in production but important during tests).
    """
    from app.services.llm_service import LLMService
    settings = get_settings()
    return LLMService(settings)


def get_llm_service(settings: Settings = Depends(get_app_settings)) -> "LLMService":
    """Provide a process-wide singleton LLMService."""
    return _cached_llm_service(
        str(id(settings)),
        settings.llm_base_url,
        settings.llm_api_key,
    )


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
