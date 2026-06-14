"""Pagination helpers."""

from math import ceil

from app.schemas.common import PaginationInfo


def build_pagination(page: int, page_size: int, max_page_size: int = 200) -> tuple[int, int]:
    """Normalize page/page_size and return (offset, limit) for SQL queries."""
    normalized_page = max(page, 1)
    normalized_page_size = min(max(page_size, 1), max_page_size)
    return (normalized_page - 1) * normalized_page_size, normalized_page_size


def build_pagination_info(page: int, page_size: int, total: int) -> PaginationInfo:
    """Build a PaginationInfo response object."""
    total_pages = ceil(total / page_size) if total else 0
    return PaginationInfo(page=page, page_size=page_size, total=total, total_pages=total_pages)
