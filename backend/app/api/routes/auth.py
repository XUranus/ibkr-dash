"""Authentication routes: login, logout, session check.

Uses HMAC-signed session tokens stored in an httpOnly cookie.
The signing secret is derived from the application's auth_password setting.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import sqlite3
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.auth import (
    AuthSession,
    DEFAULT_SESSION_MAX_AGE,
    SESSION_COOKIE_NAME,
    create_session_token,
    verify_session_token,
)
from app.core.config import Settings, get_settings
from app.core.database import get_database
from app.schemas.auth import LoginRequest, LoginResponse, SessionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Rate limiting (SQLite-backed, per-IP, persistent across restarts)
# ---------------------------------------------------------------------------

_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 300  # 5 minutes
_BLOCK_SECONDS = 900   # 15 minutes


def _ensure_rate_limit_table() -> None:
    """Create the login_attempts table if it doesn't exist."""
    try:
        db = get_database()
        db.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                ip          TEXT PRIMARY KEY,
                fail_count  INTEGER NOT NULL DEFAULT 0,
                first_fail  REAL NOT NULL,
                updated_at  REAL NOT NULL
            )
        """)
    except Exception:
        logger.warning("Failed to ensure login_attempts table")


_ensure_rate_limit_table()


def _check_rate_limit(ip: str) -> None:
    """Raise 429 if IP is rate-limited."""
    now = time.time()
    try:
        db = get_database()
        row = db.execute_one(
            "SELECT fail_count, first_fail FROM login_attempts WHERE ip = ?",
            (ip,),
        )
        if row:
            count = row["fail_count"]
            first_time = row["first_fail"]
            if now - first_time > _BLOCK_SECONDS:
                db.execute("DELETE FROM login_attempts WHERE ip = ?", (ip,))
            elif count >= _MAX_ATTEMPTS:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many login attempts. Try again later.",
                )
    except HTTPException:
        raise
    except Exception:
        logger.warning("Rate limit check failed, allowing request")


def _record_failure(ip: str) -> None:
    """Record a failed login attempt."""
    now = time.time()
    try:
        db = get_database()
        row = db.execute_one(
            "SELECT fail_count, first_fail FROM login_attempts WHERE ip = ?",
            (ip,),
        )
        if row:
            count = row["fail_count"]
            first_time = row["first_fail"]
            if now - first_time > _WINDOW_SECONDS:
                db.execute(
                    "UPDATE login_attempts SET fail_count = 1, first_fail = ?, updated_at = ? WHERE ip = ?",
                    (now, now, ip),
                )
            else:
                db.execute(
                    "UPDATE login_attempts SET fail_count = fail_count + 1, updated_at = ? WHERE ip = ?",
                    (now, ip),
                )
        else:
            db.execute(
                "INSERT INTO login_attempts (ip, fail_count, first_fail, updated_at) VALUES (?, 1, ?, ?)",
                (ip, now, now),
            )
    except Exception:
        logger.warning("Failed to record login failure for %s", ip)


def _clear_attempts(ip: str) -> None:
    """Clear attempts on successful login."""
    try:
        db = get_database()
        db.execute("DELETE FROM login_attempts WHERE ip = ?", (ip,))
    except Exception:
        logger.warning("Failed to clear login attempts for %s", ip)


def _session_secret(settings: Settings) -> str:
    """Derive a stable HMAC secret from the configured auth_password."""
    if settings.auth_password:
        return hashlib.sha256(settings.auth_password.encode()).hexdigest()
    return hashlib.sha256(b"ibkr-dash-default-secret").hexdigest()


def _get_optional_session(request: Request, settings: Settings) -> AuthSession | None:
    """Extract and verify the session cookie, if present."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    return verify_session_token(token, secret=_session_secret(settings))


@router.get("/session", response_model=SessionResponse)
def get_session(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> SessionResponse:
    """Check current session status."""
    session = _get_optional_session(request, settings)
    if session is None:
        return SessionResponse(authenticated=False)
    return SessionResponse(authenticated=True, username=session.username)


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    """Validate credentials and set a session cookie."""
    _check_rate_limit(request.client.host)

    if not settings.auth_password:
        # Auth not configured -- accept any login
        token = create_session_token(
            username=payload.username,
            secret=_session_secret(settings),
            max_age_seconds=DEFAULT_SESSION_MAX_AGE,
        )
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=token,
            max_age=DEFAULT_SESSION_MAX_AGE,
            httponly=True,
            samesite="strict",
            secure=settings.cookie_secure,
            path="/",
        )
        return LoginResponse(authenticated=True, username=payload.username)

    # Validate credentials using constant-time comparison
    correct_username = secrets.compare_digest(payload.username, settings.auth_username)
    correct_password = secrets.compare_digest(payload.password, settings.auth_password)
    if not (correct_username and correct_password):
        _record_failure(request.client.host)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    _clear_attempts(request.client.host)
    token = create_session_token(
        username=payload.username,
        secret=_session_secret(settings),
        max_age_seconds=DEFAULT_SESSION_MAX_AGE,
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=DEFAULT_SESSION_MAX_AGE,
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
        path="/",
    )
    return LoginResponse(authenticated=True, username=payload.username)


@router.post("/logout", response_model=SessionResponse)
def logout(response: Response) -> SessionResponse:
    """Clear the session cookie."""
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/", samesite="strict")
    return SessionResponse(authenticated=False)
