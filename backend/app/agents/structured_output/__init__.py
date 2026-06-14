"""Structured output framework: JSON extraction, validation, repair, fallback."""

from app.agents.structured_output.contracts import StructuredOutputContract
from app.agents.structured_output.errors import StructuredOutputError
from app.agents.structured_output.json_parser import extract_json_object
from app.agents.structured_output.runtime import StructuredOutputResult, StructuredOutputRuntime

__all__ = [
    "StructuredOutputContract",
    "StructuredOutputError",
    "StructuredOutputResult",
    "StructuredOutputRuntime",
    "extract_json_object",
]
