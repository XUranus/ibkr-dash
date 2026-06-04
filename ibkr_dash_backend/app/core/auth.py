"""Authentication helpers: HTTP Basic and HMAC session tokens.

Provides:
- ``get_current_user`` for HTTP Basic auth (existing pattern).
- ``create_session_token`` / ``verify_session_token`` for cookie-based
  session authentication used by the login/logout endpoints.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.config import Settings, get_settings

security = HTTPBasic(auto_error=False)

SESSION_COOKIE_NAME = "ibkr_dash_session"

# Default session lifetime: 7 days
DEFAULT_SESSION_MAX_AGE = 7 * 24 * 3600


# ---------------------------------------------------------------------------
# Session token (cookie-based)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthSession:
    """Verified session data extracted from a token."""
    username: str
    expires_at: int


def _urlsafe_b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _urlsafe_b64decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(f"{raw}{padding}".encode("utf-8"))


def create_session_token(*, username: str, secret: str, max_age_seconds: int = DEFAULT_SESSION_MAX_AGE) -> str:
    """Create a signed session token.

    Returns a string like ``<base64-payload>.<hex-signature>``.
    """
    expires_at = int(time.time()) + max_age_seconds
    payload = _urlsafe_b64encode(
        json.dumps({"u": username, "e": expires_at}, separators=(",", ":")).encode("utf-8")
    )
    signature = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_session_token(token: str, *, secret: str) -> AuthSession | None:
    """Verify and decode a session token.

    Returns an ``AuthSession`` on success, or ``None`` if the token is
    invalid, expired, or tampered with.
    """
    if "." not in token:
        return None

    payload, signature = token.rsplit(".", 1)
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return None

    try:
        payload_data = json.loads(_urlsafe_b64decode(payload))
    except (ValueError, json.JSONDecodeError):
        return None

    username = payload_data.get("u")
    expires_at = payload_data.get("e")
    if not isinstance(username, str) or not isinstance(expires_at, int):
        return None
    if expires_at <= int(time.time()):
        return None

    return AuthSession(username=username, expires_at=expires_at)


# ---------------------------------------------------------------------------
# HTTP Basic auth (existing pattern)
# ---------------------------------------------------------------------------


def get_current_user(
    credentials: HTTPBasicCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> str | None:
    """Validate basic auth credentials.

    Returns the username if auth is configured and credentials match.
    Returns None if auth is not configured (open access).
    Raises 401 if credentials are wrong.
    """
    if not settings.auth_password:
        return None  # Auth not configured -- open access

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )

    correct_username = secrets.compare_digest(credentials.username, settings.auth_username)
    correct_password = secrets.compare_digest(credentials.password, settings.auth_password)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
