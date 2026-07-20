"""API Token management service.

Handles generation, listing, and revocation of API tokens
used for external access (MCP integrations, etc.).

Tokens are stored as SHA-256 hashes. The raw token is only
returned once at creation time.
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Any

from app.core.database import Database

logger = logging.getLogger(__name__)

# Token prefix for easy identification
_TOKEN_PREFIX = "ibkr_"


def _generate_token() -> str:
    """Generate a secure API token with prefix."""
    return _TOKEN_PREFIX + secrets.token_urlsafe(32)


def _hash_token(token: str) -> str:
    """SHA-256 hash of a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def _token_preview(token: str) -> str:
    """Short preview of a token for display (e.g. 'ibkr_Ab3...Xy9')."""
    if len(token) <= 12:
        return token
    return token[:8] + "..." + token[-4:]


class ApiTokenService:
    """CRUD operations for API tokens."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def create_token(
        self,
        *,
        name: str = "",
        description: str = "",
        scopes: list[str] | None = None,
        expires_at: str | None = None,
    ) -> dict[str, Any]:
        """Create a new API token. Returns the token record (including the raw token)."""
        token = _generate_token()
        token_hash = _hash_token(token)
        preview = _token_preview(token)
        scopes_json = json.dumps(scopes or ["read"])
        now = datetime.now(timezone.utc).isoformat()

        row_id = self._db.insert("api_tokens", {
            "token_hash": token_hash,
            "token_preview": preview,
            "name": name,
            "description": description,
            "scopes": scopes_json,
            "expires_at": expires_at,
            "revoked": 0,
            "created_at": now,
        })

        logger.info("Created API token: name=%s", name)
        return {
            "id": row_id,
            "token": token,
            "name": name,
            "description": description,
            "scopes": scopes or ["read"],
            "expires_at": expires_at,
            "revoked": False,
            "created_at": now,
            "last_used_at": None,
        }

    def list_tokens(self) -> list[dict[str, Any]]:
        """List all tokens (token value is masked)."""
        rows = self._db.execute(
            "SELECT id, token_preview, name, description, scopes, last_used_at, expires_at, revoked, created_at "
            "FROM api_tokens ORDER BY created_at DESC"
        )
        result = []
        for row in rows:
            scopes_raw = row["scopes"]
            if isinstance(scopes_raw, str):
                try:
                    scopes = json.loads(scopes_raw)
                except (json.JSONDecodeError, TypeError):
                    scopes = []
            elif isinstance(scopes_raw, list):
                scopes = scopes_raw
            else:
                scopes = []
            result.append({
                "id": row["id"],
                "token_preview": row["token_preview"],
                "name": row["name"],
                "description": row["description"],
                "scopes": scopes,
                "last_used_at": row["last_used_at"],
                "expires_at": row["expires_at"],
                "revoked": bool(row["revoked"]),
                "created_at": row["created_at"],
            })
        return result

    def revoke_token(self, token_id: int) -> bool:
        """Revoke a token by ID. Returns True if found and revoked."""
        self._db.execute(
            "UPDATE api_tokens SET revoked = 1 WHERE id = ? AND revoked = 0",
            (token_id,),
        )
        # Check if any row was actually updated
        row = self._db.execute_one(
            "SELECT id FROM api_tokens WHERE id = ? AND revoked = 1",
            (token_id,),
        )
        if not row:
            return False
        logger.info("Revoked API token id=%d", token_id)
        return True

    def delete_token(self, token_id: int) -> bool:
        """Permanently delete a token by ID."""
        row = self._db.execute_one("SELECT id FROM api_tokens WHERE id = ?", (token_id,))
        if not row:
            return False
        self._db.execute("DELETE FROM api_tokens WHERE id = ?", (token_id,))
        logger.info("Deleted API token id=%d", token_id)
        return True

    def validate_token(self, token: str) -> dict[str, Any] | None:
        """Validate a raw token string. Returns token record if valid, None otherwise.

        Checks: token exists, not revoked, not expired.
        Also updates last_used_at.
        """
        token_hash = _hash_token(token)
        row = self._db.execute_one(
            "SELECT id, name, scopes, revoked, expires_at FROM api_tokens WHERE token_hash = ?",
            (token_hash,),
        )
        if not row:
            return None
        if row["revoked"]:
            return None

        # Check expiry — treat malformed dates as expired
        if row["expires_at"]:
            try:
                exp = datetime.fromisoformat(row["expires_at"])
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > exp:
                    return None
            except (ValueError, TypeError):
                logger.warning("Token id=%d has malformed expires_at=%s, treating as expired", row["id"], row["expires_at"])
                return None

        # Update last_used_at
        now = datetime.now(timezone.utc).isoformat()
        self._db.execute(
            "UPDATE api_tokens SET last_used_at = ? WHERE id = ?",
            (now, row["id"]),
        )

        # Parse scopes
        scopes_raw = row["scopes"]
        if isinstance(scopes_raw, str):
            try:
                scopes = json.loads(scopes_raw)
            except (json.JSONDecodeError, TypeError):
                scopes = []
        elif isinstance(scopes_raw, list):
            scopes = scopes_raw
        else:
            scopes = []

        return {
            "id": row["id"],
            "name": row["name"],
            "scopes": scopes,
        }
