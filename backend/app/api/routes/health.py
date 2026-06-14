"""Health check and cache stats endpoints."""

from fastapi import APIRouter

from app.core import cache
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    """Return service health status."""
    return HealthResponse(status="ok", service="backend")


@router.get("/cache/stats", tags=["health"])
def cache_stats() -> dict:
    """Return cache statistics."""
    return cache.stats()
