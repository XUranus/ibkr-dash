"""Admin LLM provider schemas."""

from __future__ import annotations

from pydantic import BaseModel


class LlmProviderCreate(BaseModel):
    """Request to add an LLM provider."""
    name: str
    base_url: str
    api_key: str
    default_model: str = "gpt-4o"
    temperature: float = 0.1
    max_tokens: int = 4096


class LlmProviderResponse(BaseModel):
    """An LLM provider configuration."""
    name: str
    base_url: str
    api_key_masked: str
    default_model: str
    temperature: float
    max_tokens: int
    is_active: bool = False


class LlmTestRequest(BaseModel):
    """Request to test an LLM connection."""
    message: str = "Hello, respond with a single word."


class LlmTestResponse(BaseModel):
    """Response from an LLM connection test."""
    success: bool
    model: str | None = None
    content: str | None = None
    latency_ms: int | None = None
    error: str | None = None


class LlmHealthResponse(BaseModel):
    """LLM health check response."""
    configured: bool
    base_url: str
    default_model: str
    status: str = "ok"
    message: str | None = None
