"""LLM audit logger.

Records every LLM call (model, tokens, latency, agent) to a JSONL file
for offline analysis. Controlled by the ``audit_llm_calls`` setting.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUDIT_DIR = _PROJECT_ROOT / "data" / "audit"
_AUDIT_FILE: Path | None = None


def _get_audit_path() -> Path:
    global _AUDIT_FILE
    if _AUDIT_FILE is None:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        _AUDIT_FILE = AUDIT_DIR / "llm_calls.jsonl"
    return _AUDIT_FILE


def is_enabled() -> bool:
    """Check if LLM audit logging is enabled via config."""
    try:
        from app.core.settings_manager import get_manager
        return bool(get_manager().get("advanced.audit_llm_calls", False))
    except Exception:
        return False


def log_llm_call(
    *,
    agent_name: str = "",
    model: str = "",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    latency_ms: int = 0,
    ok: bool = True,
    error: str = "",
    contract: str = "",
) -> None:
    """Append one LLM call record to the audit log (JSONL)."""
    if not is_enabled():
        return
    try:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "agent": agent_name,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "latency_ms": latency_ms,
            "ok": ok,
        }
        if error:
            record["error"] = error[:500]
        if contract:
            record["contract"] = contract
        path = _get_audit_path()
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.warning("Failed to write LLM audit log: %s", exc)
