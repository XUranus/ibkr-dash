"""Application configuration using pydantic-settings.

All settings are loaded from environment variables with sensible defaults.
No external dependencies (Redis, Elasticsearch) — SQLite is the sole store.
"""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- App ---
    app_name: str = "IBKR Dash"
    app_env: str = "development"
    debug: bool = False

    # --- SQLite ---
    sqlite_path: str = "data/ibkr_dash.db"

    # --- Cache (in-memory TTL) ---
    cache_ttl_seconds: int = 86400  # 24 hours

    # --- LLM ---
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_default_model: str = "gpt-4o"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 8192

    # --- Longbridge (optional, for public market data) ---
    longbridge_app_key: str = ""
    longbridge_app_secret: str = ""
    longbridge_access_token: str = ""

    # --- Auth ---
    auth_username: str = "admin"
    auth_password: str = ""

    # --- CORS ---
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    model_config = {"env_prefix": "", "env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Return cached singleton settings instance."""
    return Settings()
