"""Application configuration — backed by JSON settings manager.

All reads go through ``settings_manager.get_manager()``.
No environment variables. No .env file.
"""

from __future__ import annotations

from app.core.settings_manager import get_manager


class Settings:
    """Typed accessor over the JSON config.

    Attribute access maps to top-level sections:
        settings.llm_api_key  →  manager.get("llm.api_key")
    """

    # -- IBKR --
    @property
    def flex_token(self) -> str:
        """Return the IBKR Flex token."""
        return str(get_manager().get("ibkr.flex_token", ""))

    @property
    def flex_query_ids(self) -> str:
        """Return the IBKR Flex query IDs."""
        return str(get_manager().get("ibkr.flex_query_ids", ""))

    @property
    def flex_base_url(self) -> str:
        """Return the IBKR Flex base URL."""
        return str(get_manager().get("ibkr.flex_base_url", ""))

    @property
    def flex_poll_interval_seconds(self) -> int:
        """Return the Flex poll interval in seconds."""
        return int(get_manager().get("ibkr.flex_poll_interval_seconds", 10))

    @property
    def flex_max_poll_retries(self) -> int:
        """Return the maximum number of Flex poll retries."""
        return int(get_manager().get("ibkr.flex_max_poll_retries", 60))

    # -- LLM --
    @property
    def llm_api_key(self) -> str:
        """Return the LLM API key."""
        return str(get_manager().get("llm.api_key", ""))

    @property
    def llm_base_url(self) -> str:
        """Return the LLM base URL."""
        return str(get_manager().get("llm.base_url", ""))

    @property
    def llm_default_model(self) -> str:
        """Return the default LLM model name."""
        return str(get_manager().get("llm.default_model", "gpt-4o"))

    @property
    def llm_temperature(self) -> float:
        """Return the LLM sampling temperature."""
        return float(get_manager().get("llm.temperature", 0.1))

    @property
    def llm_max_tokens(self) -> int:
        """Return the LLM maximum token limit."""
        return int(get_manager().get("llm.max_tokens", 8192))

    @property
    def bls_api_key(self) -> str:
        """Return the BLS API key."""
        return str(get_manager().get("llm.bls_api_key", ""))

    # -- Scheduler --
    @property
    def scheduler_enabled(self) -> bool:
        """Return whether the scheduler is enabled."""
        return bool(get_manager().get("scheduler.enabled", True))

    @property
    def scheduler_hour(self) -> int:
        """Return the scheduler hour of day."""
        return int(get_manager().get("scheduler.hour", 12))

    @property
    def scheduler_minute(self) -> int:
        """Return the scheduler minute of hour."""
        return int(get_manager().get("scheduler.minute", 30))

    @property
    def scheduler_timezone(self) -> str:
        """Return the scheduler timezone."""
        return str(get_manager().get("scheduler.timezone", "Asia/Shanghai"))

    # -- Auth --
    @property
    def auth_username(self) -> str:
        """Return the authentication username."""
        return str(get_manager().get("auth.username", "admin"))

    @property
    def auth_password(self) -> str:
        """Return the authentication password."""
        return str(get_manager().get("auth.password", ""))

    @property
    def cookie_secure(self) -> bool:
        """Return whether session cookies require HTTPS."""
        # Default to True in production, False in development
        explicit = get_manager().get("auth.cookie_secure", None)
        if explicit is not None:
            return bool(explicit)
        return self.app_env == "production"

    # -- Longbridge --
    @property
    def longbridge_app_key(self) -> str:
        """Return the Longbridge app key."""
        return str(get_manager().get("longbridge.app_key", ""))

    @property
    def longbridge_app_secret(self) -> str:
        """Return the Longbridge app secret."""
        return str(get_manager().get("longbridge.app_secret", ""))

    @property
    def longbridge_access_token(self) -> str:
        """Return the Longbridge access token."""
        return str(get_manager().get("longbridge.access_token", ""))

    # -- Advanced --
    @property
    def app_name(self) -> str:
        """Return the application display name."""
        return str(get_manager().get("advanced.app_name", "IBKR Dash"))

    @property
    def app_env(self) -> str:
        """Return the application environment name."""
        return str(get_manager().get("advanced.app_env", "development"))

    @property
    def debug(self) -> bool:
        """Return whether debug mode is enabled."""
        return bool(get_manager().get("advanced.debug", False))

    @property
    def sqlite_path(self) -> str:
        """Return the SQLite database file path."""
        return str(get_manager().get("advanced.sqlite_path", "data/ibkr_dash.db"))

    @property
    def log_level(self) -> str:
        """Return the logging level."""
        return str(get_manager().get("advanced.log_level", "INFO"))

    @property
    def cors_origins(self) -> str:
        """Return the allowed CORS origins."""
        return str(get_manager().get("advanced.cors_origins", "http://localhost:5173"))

    @property
    def data_dir(self) -> str:
        """Return the Flex data export directory path."""
        return str(get_manager().get("advanced.data_dir", "data/flex_exports"))

    @property
    def cache_ttl_seconds(self) -> int:
        """Return the in-memory cache TTL in seconds."""
        return int(get_manager().get("advanced.cache_ttl_seconds", 86400))

    # -- Market Events --
    @property
    def market_events_sync_interval_hours(self) -> int:
        """Return the market events sync interval in hours."""
        return int(get_manager().get("scheduler.market_events_sync_interval_hours", 24))


# ---------------------------------------------------------------------------
# Singleton (no lru_cache — values are live from JSON)
# ---------------------------------------------------------------------------

_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a Settings instance backed by the JSON config."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
