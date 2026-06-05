"""Account Copilot chat endpoints.

Provides a conversational interface to the portfolio assistant agent.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_llm_service
from app.core.database import Database
from app.core.rate_limit import check_llm_rate_limit
from app.services.llm_service import LLMService

router = APIRouter(prefix="/copilot", tags=["copilot"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class CopilotChatRequest(BaseModel):
    """Chat request from the user."""
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=10000)


class CopilotChatResponse(BaseModel):
    """Response from the copilot."""
    session_id: str
    run_id: str
    answer: str
    actions: list[dict] = []
    tool_calls: list[dict] = []
    pending_approval: dict | None = None
    errors: list[str] = []


class CopilotSessionResponse(BaseModel):
    """Copilot session metadata."""
    session_id: str
    title: str = ""
    created_at: str
    message_count: int = 0


class CopilotMessageResponse(BaseModel):
    """A single message in a copilot session."""
    id: int
    session_id: str
    role: str
    content: str
    metadata: dict | None = None
    created_at: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=CopilotChatResponse)
def copilot_chat(
    request: CopilotChatRequest,
    db: Database = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service),
    _rate: None = Depends(check_llm_rate_limit),
) -> CopilotChatResponse:
    """Send a message to the Account Copilot and get a response.

    Creates a new session if session_id is not provided.
    The copilot runs in a synchronous ReAct loop (up to 8 rounds).
    """
    # Ensure session exists
    session_id = request.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        # Generate a title from the first message (max 50 chars)
        title = request.message[:50].strip()
        if len(request.message) > 50:
            title += "..."
        db.insert("copilot_sessions", {
            "id": session_id,
            "title": title,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    else:
        existing = db.execute_one(
            "SELECT id FROM copilot_sessions WHERE id = ?", (session_id,)
        )
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

    # Save user message
    db.insert("copilot_messages", {
        "session_id": session_id,
        "role": "user",
        "content": request.message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Run copilot
    try:
        from app.agents.account_copilot.runtime import AccountCopilotRuntime
        from app.agents.account_copilot.tool_registry import build_default_tool_registry
        from app.agents.account_copilot.skill_registry import build_default_skill_registry
        from app.services.ibkr_tool_service import IbkrToolService

        tool_service = IbkrToolService(db)
        tool_registry = build_default_tool_registry(tool_service)
        skill_registry = build_default_skill_registry(db)

        # Load conversation history
        history = db.execute(
            "SELECT role, content FROM copilot_messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        )

        # Build messages list from history
        messages = [{"role": h["role"], "content": h["content"]} for h in history]

        runtime = AccountCopilotRuntime(
            llm_service=llm_service,
            tool_registry=tool_registry,
            skill_registry=skill_registry,
            max_rounds=12,
            max_tokens=8192,
        )

        # Build state
        from app.agents.account_copilot.state import AccountCopilotState
        state = AccountCopilotState(
            session_id=session_id,
            run_id=str(uuid.uuid4()),
            user_input=request.message,
            messages=messages,
            rolling_summary="",
            pinned_facts=[],
            retrieved_memories=[],
            non_compressible_constraints=[],
            actions=[],
            observations=[],
            tool_calls=[],
            skill_requests=[],
            pending_approval=None,
            memory_snapshot=None,
            final_answer=None,
            errors=[],
        )

        result_state = runtime.run(state)

        answer = result_state.get("final_answer") or ""
        run_id = result_state.get("run_id", str(uuid.uuid4()))
        actions = result_state.get("actions", [])
        tool_calls = result_state.get("tool_calls", [])
        pending_approval = result_state.get("pending_approval")
        errors = [str(e) for e in result_state.get("errors", [])]

    except Exception as exc:
        answer = f"I encountered an error processing your request: {str(exc)[:200]}"
        run_id = str(uuid.uuid4())
        actions = []
        tool_calls = []
        pending_approval = None
        errors = [str(exc)[:500]]

    # Save assistant response
    db.insert("copilot_messages", {
        "session_id": session_id,
        "role": "assistant",
        "content": answer,
        "metadata": json.dumps({
            "run_id": run_id,
            "actions_count": len(actions),
            "tool_calls_count": len(tool_calls),
        }),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return CopilotChatResponse(
        session_id=session_id,
        run_id=run_id,
        answer=answer,
        actions=actions,
        tool_calls=tool_calls,
        pending_approval=pending_approval,
        errors=errors,
    )


@router.get("/sessions", response_model=list[CopilotSessionResponse])
def list_sessions(
    limit: int = 20,
    db: Database = Depends(get_db),
) -> list[CopilotSessionResponse]:
    """List copilot sessions."""
    rows = db.execute(
        "SELECT s.id as session_id, s.title, s.created_at, COUNT(m.id) as message_count "
        "FROM copilot_sessions s LEFT JOIN copilot_messages m ON s.id = m.session_id "
        "GROUP BY s.id ORDER BY s.created_at DESC LIMIT ?",
        (limit,),
    )
    return [CopilotSessionResponse(**row) for row in rows]


@router.get("/sessions/{session_id}/messages", response_model=list[CopilotMessageResponse])
def list_messages(
    session_id: str,
    limit: int = 100,
    db: Database = Depends(get_db),
) -> list[CopilotMessageResponse]:
    """List messages in a copilot session."""
    rows = db.execute(
        "SELECT id, session_id, role, content, metadata, created_at "
        "FROM copilot_messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
        (session_id, limit),
    )
    result = []
    for row in rows:
        meta = row.get("metadata")
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except (json.JSONDecodeError, TypeError):
                pass
        result.append(CopilotMessageResponse(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            metadata=meta,
            created_at=row["created_at"],
        ))
    return result


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: str,
    db: Database = Depends(get_db),
) -> None:
    """Delete a copilot session and its messages."""
    existing = db.execute_one(
        "SELECT id FROM copilot_sessions WHERE id = ?", (session_id,)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Session not found")
    db.execute("DELETE FROM copilot_messages WHERE session_id = ?", (session_id,))
    db.execute("DELETE FROM copilot_sessions WHERE id = ?", (session_id,))
