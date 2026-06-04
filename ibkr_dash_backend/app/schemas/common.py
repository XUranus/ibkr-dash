"""Common response schemas shared across all endpoints."""

from pydantic import BaseModel, Field


class PaginationInfo(BaseModel):
    """Pagination metadata included in list responses."""
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class ApiResponse(BaseModel):
    """Generic API response wrapper."""
    success: bool = True
    message: str = ""
    data: dict | None = None
