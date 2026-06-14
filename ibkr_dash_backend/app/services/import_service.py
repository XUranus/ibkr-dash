"""Import service: trigger IBKR data imports and track history.

Provides the admin scheduler API with functions to manually trigger
the import pipeline and query past import runs.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from app.core.database import Database
from app.core.settings_manager import get_manager

logger = logging.getLogger(__name__)

# Project root: ibkr_dash_backend/ -> ibkr-dash/
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_WORKER_DIR = _PROJECT_ROOT / "ibkr_dash_worker"


def _ensure_worker_importable() -> None:
    """Add the worker package parent dir to sys.path if not already present.

    The worker package lives at: <project>/ibkr_dash_worker/worker/
    So we add ibkr_dash_worker/ to sys.path so `from worker.xxx import yyy` resolves.
    """
    worker_parent = str(_WORKER_DIR)
    if worker_parent not in sys.path:
        sys.path.insert(0, worker_parent)


def run_import(db: Database) -> dict:
    """Trigger the full import pipeline (fetch + import) and log results.

    Returns:
        Dict with 'files' mapping filename to import counts,
        and 'errors' listing any failures.
    """
    _ensure_worker_importable()

    from worker.jobs.fetch_job import fetch_flex_statements
    from worker.jobs.import_job import import_all_archived

    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    t0 = time.monotonic()

    errors: list[str] = []
    files: dict[str, dict[str, int]] = {}

    # Step 1: Fetch from IBKR
    try:
        fetched = fetch_flex_statements()
        logger.info("Fetched %d files from IBKR", len(fetched))
    except Exception as exc:
        msg = f"Fetch failed: {exc}"
        logger.warning(msg)
        errors.append(msg)

    # Step 2: Import all archived files (force=True: re-import even if tracked)
    try:
        results = import_all_archived(force=True)
        for filename, counts in results.items():
            files[filename] = counts
    except Exception as exc:
        msg = f"Import failed: {exc}"
        logger.exception(msg)
        errors.append(msg)

    duration_ms = int((time.monotonic() - t0) * 1000)

    # Step 3: Log each imported file to import_history
    data_dir = Path(get_manager().get("advanced.data_dir", str(_PROJECT_ROOT / "data" / "flex_exports")))
    for filename, counts in files.items():
        file_path = data_dir / filename
        file_size = file_path.stat().st_size if file_path.exists() else 0
        try:
            db.execute(
                "INSERT INTO import_history (file_path, file_size, status, records_imported, started_at, duration_ms) VALUES (?, ?, ?, ?, ?, ?)",
                (str(file_path), file_size, "success", json.dumps(counts), started_at, duration_ms),
            )
        except Exception:
            logger.exception("Failed to log import for %s", filename)

    return {"files": files, "errors": errors, "started_at": started_at, "duration_ms": duration_ms}


def get_import_history(db: Database, limit: int = 100) -> list[dict]:
    """Return recent import history records.

    Args:
        db: Database instance.
        limit: Max records to return.

    Returns:
        List of dicts with keys: id, run_at, file_path, file_size, status, records_imported, error
    """
    rows = db.execute(
        "SELECT * FROM import_history ORDER BY run_at DESC LIMIT ?",
        (limit,),
    )
    results = []
    for row in rows:
        item = dict(row)
        # Parse records_imported JSON
        raw = item.get("records_imported")
        if raw and isinstance(raw, str):
            try:
                item["records_imported"] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                pass
        results.append(item)
    return results
