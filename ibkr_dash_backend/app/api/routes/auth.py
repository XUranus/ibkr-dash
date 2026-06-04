"""Authentication routes: login, logout, session check.

Uses HMAC-signed session tokens stored in an httpOnly cookie.
The signing secret is derived from the application's auth_password setting.
"""

from __future__ import annotations

import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.auth import (
    AuthSession,
    DEFAULT_SESSION_MAX_AGE,
    SESSION_COOKIE_NAME,
    create_session_token,
    verify_session_token,
)
from app.core.config import Settings, get_settings
from app.schemas.auth import LoginRequest, LoginResponse, SessionResponse

router = APIRouter(prefix="/auth", tags=["auth"])


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
    response: Response,
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    """Validate credentials and set a session cookie."""
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
            samesite="lax",
            secure=False,
            path="/",
        )
        return LoginResponse(authenticated=True, username=payload.username)

    # Validate credentials using constant-time comparison
    correct_username = secrets.compare_digest(payload.username, settings.auth_username)
    correct_password = secrets.compare_digest(payload.password, settings.auth_password)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

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
        samesite="lax",
        secure=False,
        path="/",
    )
    return LoginResponse(authenticated=True, username=payload.username)


@router.post("/logout", response_model=SessionResponse)
def logout(response: Response) -> SessionResponse:
    """Clear the session cookie."""
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/", samesite="lax")
    return SessionResponse(authenticated=False)
