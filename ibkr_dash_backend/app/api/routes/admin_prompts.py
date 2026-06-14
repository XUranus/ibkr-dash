"""Admin prompt management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_db
from app.core.database import Database

router = APIRouter(prefix="/admin/prompts", tags=["admin", "prompts"])


class PromptCreateRequest(BaseModel):
    """Request body for creating a new agent prompt."""
    prompt_key: str
    content: str
    status: str = "active"


class PromptResponse(BaseModel):
    """Response model representing a versioned agent prompt."""
    id: int
    prompt_key: str
    version: int
    content: str
    status: str
    created_at: str


@router.get("", response_model=list[PromptResponse])
def list_prompts(
    prompt_key: str | None = None,
    db: Database = Depends(get_db),
    _user: str | None = Depends(get_current_user),
) -> list[PromptResponse]:
    """List all prompt versions, optionally filtered by key."""
    if prompt_key:
        rows = db.execute(
            "SELECT * FROM agent_prompts WHERE prompt_key = ? ORDER BY version DESC",
            (prompt_key,),
        )
    else:
        rows = db.execute(
            "SELECT * FROM agent_prompts ORDER BY prompt_key, version DESC"
        )
    return [PromptResponse(**row) for row in rows]


@router.post("", response_model=PromptResponse)
def create_prompt(
    request: PromptCreateRequest,
    db: Database = Depends(get_db),
    _user: str | None = Depends(get_current_user),
) -> PromptResponse:
    """Create a new prompt version."""
    # Get next version number
    existing = db.execute_one(
        "SELECT MAX(version) as max_ver FROM agent_prompts WHERE prompt_key = ?",
        (request.prompt_key,),
    )
    next_version = (existing["max_ver"] or 0) + 1 if existing else 1

    row_id = db.insert("agent_prompts", {
        "prompt_key": request.prompt_key,
        "version": next_version,
        "content": request.content,
        "status": request.status,
    })

    row = db.execute_one("SELECT * FROM agent_prompts WHERE id = ?", (row_id,))
    return PromptResponse(**row)


@router.get("/{prompt_key}/active", response_model=PromptResponse)
def get_active_prompt(
    prompt_key: str,
    db: Database = Depends(get_db),
    _user: str | None = Depends(get_current_user),
) -> PromptResponse:
    """Get the active version of a prompt."""
    row = db.execute_one(
        "SELECT * FROM agent_prompts WHERE prompt_key = ? AND status = 'active' ORDER BY version DESC LIMIT 1",
        (prompt_key,),
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"No active prompt found for key: {prompt_key}")
    return PromptResponse(**row)
