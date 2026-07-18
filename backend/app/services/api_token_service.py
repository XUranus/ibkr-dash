"""API Token management service.

Handles generation, listing, and revocation of API tokens
used for external access (MCP integrations, etc.).
"""

from __future__ import annotations

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
        scopes_json = str(scopes or ["read"])
        now = datetime.now(timezone.utc).isoformat()

        self._db.insert("api_tokens", {
            "token": token,
            "name": name,
            "description": description,
            "scopes": scopes_json,
            "expires_at": expires_at,
            "revoked": 0,
            "created_at": now,
        })

        logger.info("Created API token: name=%s", name)
        return {
            "id": self._db.execute_one(
                "SELECT id FROM api_tokens WHERE token = ?", (token,)
            )["id"],
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
            "SELECT id, token, name, description, scopes, last_used_at, expires_at, revoked, created_at "
            "FROM api_tokens ORDER BY created_at DESC"
        )
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "token_preview": row["token"][:8] + "..." + row["token"][-4:],
                "name": row["name"],
                "description": row["description"],
                "scopes": row["scopes"],
                "last_used_at": row["last_used_at"],
                "expires_at": row["expires_at"],
                "revoked": bool(row["revoked"]),
                "created_at": row["created_at"],
            })
        return result

    def revoke_token(self, token_id: int) -> bool:
        """Revoke a token by ID. Returns True if found and revoked."""
        row = self._db.execute_one("SELECT id FROM api_tokens WHERE id = ?", (token_id,))
        if not row:
            return False
        self._db.execute(
            "UPDATE api_tokens SET revoked = 1 WHERE id = ?", (token_id,)
        )
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
        row = self._db.execute_one(
            "SELECT id, name, scopes, revoked, expires_at FROM api_tokens WHERE token = ?",
            (token,),
        )
        if not row:
            return None
        if row["revoked"]:
            return None

        # Check expiry
        if row["expires_at"]:
            try:
                exp = datetime.fromisoformat(row["expires_at"])
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > exp:
                    return None
            except (ValueError, TypeError):
                pass

        # Update last_used_at
        now = datetime.now(timezone.utc).isoformat()
        self._db.execute(
            "UPDATE api_tokens SET last_used_at = ? WHERE id = ?",
            (now, row["id"]),
        )

        return {
            "id": row["id"],
            "name": row["name"],
            "scopes": row["scopes"],
        }
