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
    assert service.temperature == 0.1
    assert service.max_tokens == 4096


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


@patch("app.services.llm_service.httpx.Client")
def test_chat_returns_content(mock_client_class, llm_service: LLMService) -> None:
    """Test that chat() extracts content from a mocked response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello, world!"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }

    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client_class.return_value = mock_client

    result = llm_service.chat([{"role": "user", "content": "Hi"}])
    assert result == "Hello, world!"


@patch("app.services.llm_service.httpx.Client")
def test_chat_with_metadata_returns_usage(mock_client_class, llm_service: LLMService) -> None:
    """Test that chat_with_metadata() returns usage and latency info."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Response"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }

    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client_class.return_value = mock_client

    result = llm_service.chat_with_metadata([{"role": "user", "content": "Hi"}])
    assert result["content"] == "Response"
    assert result["usage"]["prompt_tokens"] == 10
    assert result["usage"]["completion_tokens"] == 5
    assert "latency_ms" in result


@patch("app.services.llm_service.httpx.Client")
def test_chat_raises_on_auth_failure(mock_client_class, llm_service: LLMService) -> None:
    """Test that chat() raises LLMClientError on 401."""
    mock_response = MagicMock()
    mock_response.status_code = 401

    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client_class.return_value = mock_client

    with pytest.raises(LLMClientError) as exc_info:
        llm_service.chat([{"role": "user", "content": "Hi"}])
    assert exc_info.value.error_code == "AUTH_FAILED"


@patch("app.services.llm_service.httpx.Client")
def test_chat_raises_on_rate_limit(mock_client_class, llm_service: LLMService) -> None:
    """Test that chat() raises LLMClientError on 429."""
    mock_response = MagicMock()
    mock_response.status_code = 429

    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client_class.return_value = mock_client

    with pytest.raises(LLMClientError) as exc_info:
        llm_service.chat([{"role": "user", "content": "Hi"}])
    assert exc_info.value.error_code == "RATE_LIMITED"


@patch("app.services.llm_service.httpx.Client")
def test_chat_raises_on_server_error(mock_client_class, llm_service: LLMService) -> None:
    """Test that chat() raises LLMClientError on 500."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.return_value = {"error": {"message": "Internal error"}}

    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client_class.return_value = mock_client

    with pytest.raises(LLMClientError) as exc_info:
        llm_service.chat([{"role": "user", "content": "Hi"}])
    assert exc_info.value.error_code == "PROVIDER_ERROR"


@patch("app.services.llm_service.httpx.Client")
def test_chat_passes_model_override(mock_client_class, llm_service: LLMService) -> None:
    """Test that chat() passes model override to the API."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {},
    }

    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client_class.return_value = mock_client

    llm_service.chat(
        [{"role": "user", "content": "Hi"}],
        model="gpt-3.5-turbo",
        temperature=0.5,
        max_tokens=100,
    )

    call_kwargs = mock_client.post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert payload["model"] == "gpt-3.5-turbo"
    assert payload["temperature"] == 0.5
    assert payload["max_tokens"] == 100
