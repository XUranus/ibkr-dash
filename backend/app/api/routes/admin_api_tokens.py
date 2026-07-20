"""Admin API Token management endpoints.

Provides CRUD operations for API tokens used by external integrations.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_db, require_admin_session
from app.core.database import Database
from app.services.api_token_service import ApiTokenService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/api-tokens", tags=["admin"])


class CreateTokenRequest(BaseModel):
    name: str = ""
    description: str = ""
    scopes: list[str] = Field(default_factory=lambda: ["read"])
    expires_at: str | None = None


class TokenResponse(BaseModel):
    id: int
    token: str | None = None  # Only present on creation
    token_preview: str | None = None
    name: str
    description: str
    scopes: Any
    last_used_at: str | None = None
    expires_at: str | None = None
    revoked: bool = False
    created_at: str | None = None


@router.get("")
def list_tokens(
    db: Database = Depends(get_db),
    _user: str | None = Depends(require_admin_session),
) -> list[dict]:
    """List all API tokens (token values are masked)."""
    svc = ApiTokenService(db)
    return svc.list_tokens()


@router.post("", status_code=201)
def create_token(
    req: CreateTokenRequest,
    db: Database = Depends(get_db),
    _user: str | None = Depends(require_admin_session),
) -> dict:
    """Create a new API token. The full token is only returned once."""
    svc = ApiTokenService(db)
    result = svc.create_token(
        name=req.name,
        description=req.description,
        scopes=req.scopes,
        expires_at=req.expires_at,
    )
    return result


@router.post("/{token_id}/revoke")
def revoke_token(
    token_id: int,
    db: Database = Depends(get_db),
    _user: str | None = Depends(require_admin_session),
) -> dict:
    """Revoke an API token."""
    svc = ApiTokenService(db)
    if not svc.revoke_token(token_id):
        raise HTTPException(status_code=404, detail="Token not found")
    return {"success": True, "message": "Token revoked"}


@router.delete("/{token_id}")
def delete_token(
    token_id: int,
    db: Database = Depends(get_db),
    _user: str | None = Depends(require_admin_session),
) -> dict:
    """Permanently delete an API token."""
    svc = ApiTokenService(db)
    if not svc.delete_token(token_id):
        raise HTTPException(status_code=404, detail="Token not found")
    return {"success": True, "message": "Token deleted"}
