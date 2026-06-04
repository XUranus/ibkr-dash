"""Admin LLM provider management endpoints.

Provides routes for listing providers, adding providers, testing LLM
connections, and health checks.  In the simplified SQLite backend the
LLM configuration is stored in environment settings rather than a
separate providers table.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_llm_service
from app.core.config import Settings, get_settings
from app.schemas.admin_llm import (
    LlmHealthResponse,
    LlmProviderCreate,
    LlmProviderResponse,
    LlmTestRequest,
    LlmTestResponse,
)
from app.services.llm_service import LLMClientError, LLMService

router = APIRouter(prefix="/admin/llm", tags=["admin-llm"])
logger = logging.getLogger(__name__)


@router.get("/providers", response_model=list[LlmProviderResponse])
def list_providers(
    _user: str | None = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> list[LlmProviderResponse]:
    """List configured LLM providers.

    In the simplified backend, the active configuration from settings
    is returned as a single provider entry.
    """
    masked_key = ""
    if settings.llm_api_key:
        key = settings.llm_api_key
        masked_key = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"

    return [
        LlmProviderResponse(
            name="default",
            base_url=settings.llm_base_url,
            api_key_masked=masked_key,
            default_model=settings.llm_default_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            is_active=True,
        )
    ]


@router.post("/providers", response_model=LlmProviderResponse)
def add_provider(
    payload: LlmProviderCreate,
    _user: str | None = Depends(get_current_user),
) -> LlmProviderResponse:
    """Register a new LLM provider.

    In the simplified SQLite backend this is a no-op that echoes back
    the provided configuration.  A full implementation would persist
    the provider to a database table.
    """
    masked_key = ""
    if payload.api_key:
        key = payload.api_key
        masked_key = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"

    return LlmProviderResponse(
        name=payload.name,
        base_url=payload.base_url,
        api_key_masked=masked_key,
        default_model=payload.default_model,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        is_active=False,
    )


@router.post("/test", response_model=LlmTestResponse)
def test_llm_connection(
    payload: LlmTestRequest,
    llm_service: LLMService = Depends(get_llm_service),
    _user: str | None = Depends(get_current_user),
) -> LlmTestResponse:
    """Test the active LLM connection with a simple chat request."""
    try:
        started = time.perf_counter()
        result = llm_service.chat_with_metadata(
            [
                {"role": "system", "content": "You are a concise assistant. Respond with a single word."},
                {"role": "user", "content": payload.message},
            ],
        )
        latency_ms = int((time.perf_counter() - started) * 1000)

        return LlmTestResponse(
            success=True,
            model=llm_service.default_model,
            content=result.get("content", ""),
            latency_ms=latency_ms,
        )
    except LLMClientError as exc:
        return LlmTestResponse(
            success=False,
            error=f"{exc.error_code}: {exc.message}",
        )
    except Exception as exc:
        return LlmTestResponse(
            success=False,
            error=str(exc)[:300],
        )


@router.get("/health", response_model=LlmHealthResponse)
def llm_health(
    settings: Settings = Depends(get_settings),
    _user: str | None = Depends(get_current_user),
) -> LlmHealthResponse:
    """Check LLM configuration health."""
    configured = bool(settings.llm_api_key)
    return LlmHealthResponse(
        configured=configured,
        base_url=settings.llm_base_url,
        default_model=settings.llm_default_model,
        status="ok" if configured else "not_configured",
        message="LLM is configured and ready" if configured else "LLM API key is not set",
    )
