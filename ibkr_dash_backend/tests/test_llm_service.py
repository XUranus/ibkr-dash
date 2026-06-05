"""Tests for the LLM service."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.services.llm_service import LLMClientError, LLMService


@pytest.fixture
def settings() -> Settings:
    """Return test settings with in-memory SQLite."""
    return Settings(
        sqlite_path=":memory:",
        debug=True,
        auth_password="",
        llm_api_key="test-key",
        llm_base_url="https://api.example.com/v1",
        llm_default_model="gpt-4o",
        llm_temperature=0.1,
        llm_max_tokens=4096,
    )


@pytest.fixture
def llm_service(settings: Settings) -> LLMService:
    """Return an LLMService instance."""
    return LLMService(settings)


def test_llm_service_configuration(settings: Settings) -> None:
    """Test that LLMService reads configuration correctly."""
    service = LLMService(settings)
    assert service.base_url == "https://api.example.com/v1"
    assert service.api_key == "test-key"
    assert service.default_model == "gpt-4o"


def test_llm_service_strips_trailing_slash_from_base_url() -> None:
    """Test that base URL trailing slash is stripped."""
    s = Settings(
        sqlite_path=":memory:", debug=True, auth_password="",
        llm_api_key="k", llm_base_url="https://api.example.com/v1/",
    )
    service = LLMService(s)
    assert service.base_url == "https://api.example.com/v1"


def test_llm_client_error_has_code_and_message() -> None:
    """Test that LLMClientError carries error code and message."""
    err = LLMClientError("TIMEOUT", "request timed out")
    assert err.error_code == "TIMEOUT"
    assert str(err) == "request timed out"


def test_chat_returns_content(llm_service: LLMService) -> None:
    """Test that chat() extracts content from a mocked response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello, world!"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }

    # Mock the persistent client's post method
    llm_service._client = MagicMock()
    llm_service._client.post.return_value = mock_response

    result = llm_service.chat([{"role": "user", "content": "Hi"}])
    assert result == "Hello, world!"


def test_chat_with_metadata_returns_usage(llm_service: LLMService) -> None:
    """Test that chat_with_metadata() returns usage and latency info."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "OK"}}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
    }

    llm_service._client = MagicMock()
    llm_service._client.post.return_value = mock_response

    result = llm_service.chat_with_metadata([{"role": "user", "content": "Test"}])
    assert result["content"] == "OK"
    assert result["usage"]["prompt_tokens"] == 20
    assert result["usage"]["total_tokens"] == 30
    assert result["latency_ms"] >= 0


def test_chat_raises_on_auth_failure(llm_service: LLMService) -> None:
    """Test that auth failure raises LLMClientError with AUTH_FAILED."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {"error": {"message": "Invalid API key"}}

    llm_service._client = MagicMock()
    llm_service._client.post.return_value = mock_response

    with pytest.raises(LLMClientError) as exc_info:
        llm_service.chat([{"role": "user", "content": "Hi"}])
    assert exc_info.value.error_code == "AUTH_FAILED"


def test_chat_raises_on_rate_limit(llm_service: LLMService) -> None:
    """Test that rate limit raises LLMClientError with RATE_LIMITED."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.json.return_value = {"error": {"message": "Rate limited"}}

    llm_service._client = MagicMock()
    llm_service._client.post.return_value = mock_response

    with pytest.raises(LLMClientError) as exc_info:
        llm_service.chat([{"role": "user", "content": "Hi"}])
    assert exc_info.value.error_code == "RATE_LIMITED"


def test_chat_passes_model_override(llm_service: LLMService) -> None:
    """Test that model override is passed to the API."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "OK"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
    }

    llm_service._client = MagicMock()
    llm_service._client.post.return_value = mock_response

    llm_service.chat([{"role": "user", "content": "Test"}], model="gpt-4o-mini")

    call_args = llm_service._client.post.call_args
    payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][2]
    assert payload["model"] == "gpt-4o-mini"


def test_chat_with_response_format(llm_service: LLMService) -> None:
    """Test that response_format is passed when specified."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"key": "value"}'}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
    }

    llm_service._client = MagicMock()
    llm_service._client.post.return_value = mock_response

    llm_service.chat(
        [{"role": "user", "content": "Return JSON"}],
        response_format={"type": "json_object"},
    )

    call_args = llm_service._client.post.call_args
    payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][2]
    assert payload["response_format"] == {"type": "json_object"}
