"""Admin Flex Report management endpoints.

Provides list, delete, download, and bulk-download for flex_exports files.
"""

from __future__ import annotations

import io
import logging
import os
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.core.config import get_settings

router = APIRouter(prefix="/admin/flex-reports", tags=["admin-flex-reports"])
logger = logging.getLogger(__name__)


def _get_flex_dir() -> Path:
    """Return the flex_exports directory path."""
    settings = get_settings()
    return Path(settings.data_dir)


@router.get("")
def list_flex_reports(
    _user: str | None = Depends(get_current_user),
) -> list[dict]:
    """List all flex export files with metadata."""
    flex_dir = _get_flex_dir()
    if not flex_dir.exists():
        return []

    files: list[dict] = []
    for f in sorted(flex_dir.iterdir(), reverse=True):
        if f.name.startswith(".") or f.name == "imported_files.txt":
            continue
        if f.suffix not in (".xml", ".csv", ".txt"):
            continue
        stat = f.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        files.append({
            "name": f.name,
            "size": stat.st_size,
            "modified_at": mtime.isoformat(),
            "query_id": f.stem.rsplit("_", 1)[0] if "_" in f.stem else f.stem,
        })
    return files


@router.delete("/{filename}")
def delete_flex_report(
    filename: str,
    _user: str | None = Depends(get_current_user),
) -> dict:
    """Delete a single flex export file."""
    flex_dir = _get_flex_dir()
    file_path = flex_dir / filename

    # Security: prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    file_path.unlink()
    logger.info("Deleted flex report: %s", filename)
    return {"deleted": filename}


@router.get("/download/{filename}")
def download_flex_report(
    filename: str,
    _user: str | None = Depends(get_current_user),
) -> StreamingResponse:
    """Download a single flex export file."""
    flex_dir = _get_flex_dir()
    file_path = flex_dir / filename

    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    def file_iterator():
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                yield chunk

    return StreamingResponse(
        file_iterator(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/download-all")
def download_all_flex_reports(
    _user: str | None = Depends(get_current_user),
) -> StreamingResponse:
    """Download all flex export files as a zip archive."""
    flex_dir = _get_flex_dir()
    if not flex_dir.exists():
        raise HTTPException(status_code=404, detail="No flex exports directory")

    files = [
        f for f in flex_dir.iterdir()
        if f.is_file() and not f.name.startswith(".") and f.name != "imported_files.txt"
        and f.suffix in (".xml", ".csv", ".txt")
    ]
    if not files:
        raise HTTPException(status_code=404, detail="No flex export files found")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, f.name)
    buf.seek(0)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    zip_name = f"flex_reports_{timestamp}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )
