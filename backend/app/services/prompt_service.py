"""Prompt service: loads admin-managed prompts from the database."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from app.core.database import Database

logger = logging.getLogger(__name__)


class PromptService:
    """Service for loading runtime prompts from the database."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def get_runtime_prompt(
        self,
        prompt_key: str,
        fallback: str = "",
    ) -> dict[str, Any] | None:
        """Get the active prompt for a given key.

        Args:
            prompt_key: The prompt key to look up.
            fallback: Default content if no active prompt found.

        Returns:
            Dict with 'content' and 'metadata' keys, or None if not found.
        """
        row = self.db.execute_one(
            "SELECT id, prompt_key, version, content, status, created_at "
            "FROM agent_prompts WHERE prompt_key = ? AND status = 'active' "
            "ORDER BY version DESC LIMIT 1",
            (prompt_key,),
        )

        if row:
            content = str(row["content"] or "").strip()
            if content:
                return {
                    "content": content,
                    "metadata": {
                        "prompt_key": row["prompt_key"],
                        "version": row["version"],
                        "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                        "source": "admin_active",
                    },
                }

        # No active prompt found, use fallback
        if fallback:
            return {
                "content": fallback,
                "metadata": {
                    "prompt_key": prompt_key,
                    "version": None,
                    "content_hash": hashlib.sha256(fallback.encode("utf-8")).hexdigest(),
                    "source": "fallback",
                },
            }

        return None

    def list_prompts(self, prompt_key: str | None = None) -> list[dict]:
        """List all prompt versions, optionally filtered by key."""
        if prompt_key:
            rows = self.db.execute(
                "SELECT * FROM agent_prompts WHERE prompt_key = ? ORDER BY version DESC",
                (prompt_key,),
            )
        else:
            rows = self.db.execute(
                "SELECT * FROM agent_prompts ORDER BY prompt_key, version DESC"
            )
        return [dict(row) for row in rows]

    def get_active_version(self, prompt_key: str) -> dict | None:
        """Get the active version of a prompt by key."""
        row = self.db.execute_one(
            "SELECT * FROM agent_prompts WHERE prompt_key = ? AND status = 'active' "
            "ORDER BY version DESC LIMIT 1",
            (prompt_key,),
        )
        return dict(row) if row else None


__all__ = ["PromptService"]
