"""Tests for the worker configuration module."""

from worker.core.config import get_settings


def test_settings_loads_defaults(monkeypatch) -> None:
    """Test that Settings loads sensible defaults when config file is absent."""
    settings = get_settings()

    assert settings.app_env == "development"
    assert settings.scheduler_hour == 12
    assert settings.scheduler_minute == 30
    assert settings.scheduler_timezone == "Asia/Shanghai"
    assert settings.log_level == "INFO"
    assert settings.flex_poll_interval_seconds == 10
    assert settings.flex_max_poll_retries == 60
    assert "interactivebrokers.com" in settings.flex_base_url
    assert settings.market_events_sync_interval_hours == 24


def test_flex_polling_defaults_wait_long_enough_for_slow_statement_generation() -> None:
    """Test that the default polling config allows enough time for slow generation."""
    settings = get_settings()

    assert settings.flex_poll_interval_seconds == 10
    assert settings.flex_max_poll_retries == 60
    # Total wait time should be at least 600 seconds (10 minutes)
    assert settings.flex_poll_interval_seconds * settings.flex_max_poll_retries >= 600


def test_settings_is_frozen() -> None:
    """Test that Settings instances are immutable (frozen dataclass)."""
    settings = get_settings()

    try:
        settings.app_env = "changed"  # type: ignore
        assert False, "Should have raised FrozenInstanceError"
    except AttributeError:
        pass
