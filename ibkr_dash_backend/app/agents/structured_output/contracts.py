"""Structured output contracts: define schema, repair, and fallback behavior."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel

from app.agents.structured_output.errors import StructuredOutputError, preview_text


DEFAULT_REPAIR_SYSTEM_PROMPT = """You are a structured JSON repair agent.
Your task is NOT to re-analyze business logic, but to fix the existing model output so it conforms to the specified schema.
You may only use information already present in the original output and context.
Do not fabricate facts, numbers, news, financial data, or trading recommendations.
If a field is missing and cannot be determined from the original output or context, fill null, empty string, empty array, or note it in data_limitations.
Output only a JSON object. No Markdown, no explanation, no code blocks."""


FallbackBuilder = Callable[[dict[str, Any] | None, StructuredOutputError, str], dict[str, Any] | BaseModel]
RepairPromptBuilder = Callable[["StructuredOutputContract", str, StructuredOutputError, dict[str, Any] | None], list[dict[str, str]]]


@dataclass
class StructuredOutputContract:
    """Defines how to parse, validate, repair, and fallback for a structured LLM output."""

    name: str
    agent_name: str
    node_name: str
    output_model: type[BaseModel] | None = None
    schema_hint: dict[str, Any] | str | None = None
    examples: list[dict[str, Any] | str] = field(default_factory=list)
    max_repair_attempts: int = 1
    response_format: dict[str, str] = field(default_factory=lambda: {"type": "json_object"})
    repair_enabled: bool = True
    fallback_enabled: bool = True
    fallback_builder: FallbackBuilder | None = None
    repair_system_prompt: str | None = None
    repair_user_prompt_builder: RepairPromptBuilder | None = None

    def build_repair_messages(
        self,
        *,
        raw_response: str,
        error: StructuredOutputError,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, str]]:
        if self.repair_user_prompt_builder is not None:
            return self.repair_user_prompt_builder(self, raw_response, error, context)
        return build_default_repair_messages(self, raw_response=raw_response, error=error, context=context)


def build_default_repair_messages(
    contract: StructuredOutputContract,
    *,
    raw_response: str,
    error: StructuredOutputError,
    context: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    user_prompt = "\n".join([
        f"contract_name: {contract.name}",
        f"agent_name: {contract.agent_name}",
        f"node_name: {contract.node_name}",
        "schema_hint:",
        _format_jsonish(contract.schema_hint),
        "examples:",
        _format_jsonish(contract.examples),
        f"error_code: {error.error_code}",
        "validation_error:",
        error.validation_error or error.message,
        "raw_response:",
        preview_text(raw_response, max_chars=8000) or "",
        "context_preview:",
        _context_preview(context),
        "",
        "Fix only format and schema issues. Do not add new facts. Output strict JSON object only.",
    ])
    return [
        {"role": "system", "content": contract.repair_system_prompt or DEFAULT_REPAIR_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def _format_jsonish(value: Any) -> str:
    if value is None:
        return "{}"
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, indent=2, default=str)
    except TypeError:
        return str(value)


def _context_preview(context: dict[str, Any] | None) -> str:
    if not context:
        return "{}"
    try:
        text = json.dumps(context, ensure_ascii=False, default=str)
    except TypeError:
        text = str(context)
    return preview_text(text, max_chars=8000) or "{}"
