"""Tests for the worker configuration module."""

from worker.core.config import get_settings


def test_settings_loads_defaults(monkeypatch) -> None:
    """Test that Settings loads sensible defaults when env vars are not set."""
    # Clear any cached settings
    get_settings.cache_clear()

    # Clear relevant env vars to ensure defaults are used
    for var in [
        "APP_ENV", "SQLITE_PATH", "DATA_DIR", "SCHEDULER_ENABLED",
        "SCHEDULER_HOUR", "SCHEDULER_MINUTE", "SCHEDULER_TIMEZONE",
        "LOG_LEVEL", "FLEX_BASE_URL", "FLEX_TOKEN", "FLEX_QUERY_ID_DAILY",
        "FLEX_POLL_INTERVAL_SECONDS", "FLEX_MAX_POLL_RETRIES",
        "BACKEND_BASE_URL", "DAILY_REVIEW_INTERNAL_TOKEN",
    ]:
        monkeypatch.delenv(var, raising=False)

    settings = get_settings()

    assert settings.app_env == "development"
    assert settings.scheduler_hour == 12
    assert settings.scheduler_minute == 30
    assert settings.scheduler_timezone == "Asia/Shanghai"
    assert settings.log_level == "INFO"
    assert settings.flex_poll_interval_seconds == 10
    assert settings.flex_max_poll_retries == 60
    assert "interactivebrokers.com" in settings.flex_base_url
    assert settings.flex_token == ""

    get_settings.cache_clear()


def test_settings_loads_from_env(monkeypatch) -> None:
    """Test that Settings loads values from environment variables."""
    get_settings.cache_clear()

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SCHEDULER_HOUR", "8")
    monkeypatch.setenv("SCHEDULER_MINUTE", "0")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("FLEX_TOKEN", "test-token-123")
    monkeypatch.setenv("FLEX_QUERY_ID_DAILY", "99999")
    monkeypatch.setenv("BACKEND_BASE_URL", "http://backend:9000")

    settings = get_settings()

    assert settings.app_env == "production"
    assert settings.scheduler_hour == 8
    assert settings.scheduler_minute == 0
    assert settings.log_level == "WARNING"
    assert settings.flex_token == "test-token-123"
    assert settings.flex_query_id_daily == "99999"
    assert settings.backend_base_url == "http://backend:9000"

    get_settings.cache_clear()


def test_flex_polling_defaults_wait_long_enough_for_slow_statement_generation(monkeypatch) -> None:
    """Test that the default polling config allows enough time for slow generation."""
    get_settings.cache_clear()

    monkeypatch.delenv("FLEX_POLL_INTERVAL_SECONDS", raising=False)
    monkeypatch.delenv("FLEX_MAX_POLL_RETRIES", raising=False)

    settings = get_settings()

    assert settings.flex_poll_interval_seconds == 10
    assert settings.flex_max_poll_retries == 60
    # Total wait time should be at least 600 seconds (10 minutes)
    assert settings.flex_poll_interval_seconds * settings.flex_max_poll_retries >= 600

    get_settings.cache_clear()


def test_settings_is_frozen() -> None:
    """Test that Settings instances are immutable (frozen dataclass)."""
    get_settings.cache_clear()

    settings = get_settings()

    try:
        settings.app_env = "changed"  # type: ignore
        assert False, "Should have raised FrozenInstanceError"
    except AttributeError:
        pass

    get_settings.cache_clear()
