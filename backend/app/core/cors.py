"""CORS configuration helper."""

from __future__ import annotations

from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings


def add_cors_middleware(app, settings: Settings) -> None:
    """Add CORS middleware to the FastAPI app."""
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
