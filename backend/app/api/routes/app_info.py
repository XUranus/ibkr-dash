"""Public app info endpoint (no auth required)."""

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings

router = APIRouter(tags=["app-info"])


@router.get("/app-info")
def get_app_info(settings: Settings = Depends(get_settings)) -> dict:
    """Return public application info (no authentication required)."""
    return {"app_name": settings.app_name}
