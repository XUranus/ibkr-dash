"""Lightweight LLM client wrapper using an OpenAI-compatible API.

Uses httpx to call any OpenAI-compatible chat completions endpoint.
No Redis, no external storage -- just a thin HTTP client.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import Settings
from app.services.llm_audit import log_llm_call

logger = logging.getLogger(__name__)

DEFAULT_CONTEXT_WINDOW_TOKENS = 200000
DEFAULT_INPUT_TOKEN_LIMIT = 120000
DEFAULT_OUTPUT_TOKEN_LIMIT = 16000


class LLMClientError(RuntimeError):
    """Raised when an LLM provider call fails."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class LLMConfigError(ValueError):
    """Raised when LLM configuration is invalid."""


class LLMService:
    """Simple wrapper around an OpenAI-compatible chat completions endpoint."""

    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.default_model = settings.llm_default_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        self.timeout = 60.0
        self._client = httpx.Client(
            timeout=self.timeout,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
        timeout: float | None = None,
    ) -> str:
        """Send a chat completion request and return the assistant content."""
        result = self.chat_with_metadata(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            timeout=timeout,
        )
        return str(result.get("content") or "")

    def chat_with_metadata(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Send a chat completion request and return the full response dict.

        Returns a dict with keys: content, usage, latency_ms.
        """
        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        effective_timeout = timeout or self.timeout

        model_name = payload["model"]
        started = time.perf_counter()
        try:
            response = self._client.post(url, headers=headers, json=payload, timeout=effective_timeout)
        except httpx.TimeoutException as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            logger.error("LLM request timed out after %dms (model=%s)", latency_ms, model_name)
            log_llm_call(model=model_name, latency_ms=latency_ms, ok=False, error="TIMEOUT")
            raise LLMClientError("TIMEOUT", "LLM provider request timed out") from exc
        except httpx.HTTPError as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            logger.error("LLM request failed after %dms (model=%s): %s", latency_ms, model_name, exc)
            log_llm_call(model=model_name, latency_ms=latency_ms, ok=False, error=str(exc)[:500])
            raise LLMClientError("PROVIDER_ERROR", "Failed to call LLM provider") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)

        if response.status_code in {401, 403}:
            logger.error("LLM auth failed (model=%s, status=%d)", model_name, response.status_code)
            log_llm_call(model=model_name, latency_ms=latency_ms, ok=False, error="AUTH_FAILED")
            raise LLMClientError("AUTH_FAILED", "LLM provider authentication failed")
        if response.status_code == 429:
            logger.warning("LLM rate limited (model=%s)", model_name)
            log_llm_call(model=model_name, latency_ms=latency_ms, ok=False, error="RATE_LIMITED")
            raise LLMClientError("RATE_LIMITED", "LLM provider rate limit exceeded")
        if response.status_code >= 400:
            detail = ""
            try:
                err = response.json()
                detail = err.get("error", {}).get("message", "") if isinstance(err, dict) else ""
            except ValueError:
                detail = response.text[:200]
            logger.error("LLM provider error (model=%s, status=%d): %s", model_name, response.status_code, detail)
            log_llm_call(model=model_name, latency_ms=latency_ms, ok=False, error=f"HTTP {response.status_code}: {detail}")
            raise LLMClientError(
                "PROVIDER_ERROR",
                f"LLM provider error ({response.status_code}): {detail}",
            )

        try:
            data = response.json()
        except ValueError as exc:
            logger.error("LLM returned invalid JSON (model=%s)", model_name)
            log_llm_call(model=model_name, latency_ms=latency_ms, ok=False, error="INVALID_JSON")
            raise LLMClientError("PROVIDER_ERROR", "LLM provider returned invalid JSON") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("LLM unexpected response structure (model=%s): %s", model_name, list(data.keys()))
            log_llm_call(model=model_name, latency_ms=latency_ms, ok=False, error="UNEXPECTED_STRUCTURE")
            raise LLMClientError("PROVIDER_ERROR", "Unexpected response structure") from exc

        usage = data.get("usage") or {}
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)

        logger.info(
            "LLM call ok (model=%s, latency=%dms, tokens=%d/%d/%d)",
            model_name, latency_ms, prompt_tokens, completion_tokens, total_tokens,
        )
        log_llm_call(
            model=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            ok=True,
        )

        return {
            "content": content,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
            "latency_ms": latency_ms,
        }
