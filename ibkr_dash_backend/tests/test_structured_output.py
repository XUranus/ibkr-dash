"""Structured output framework tests."""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from app.agents.structured_output.json_parser import extract_json_object
from app.agents.structured_output.contracts import StructuredOutputContract
from app.agents.structured_output.errors import StructuredOutputError


# ---------------------------------------------------------------------------
# JSON parser tests
# ---------------------------------------------------------------------------


class TestExtractJsonObject:
    def test_valid_json(self):
        result = extract_json_object('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_with_markdown_fence(self):
        raw = '```json\n{"key": "value"}\n```'
        result = extract_json_object(raw)
        assert result == {"key": "value"}

    def test_json_with_surrounding_text(self):
        raw = 'Here is the result: {"key": "value"} and more text'
        result = extract_json_object(raw)
        assert result == {"key": "value"}

    def test_json_with_thinking_tags(self):
        raw = '<thinking>I should output JSON</thinking>\n{"key": "value"}'
        result = extract_json_object(raw)
        assert result == {"key": "value"}

    def test_invalid_json_raises(self):
        with pytest.raises(StructuredOutputError):
            extract_json_object("not json at all")

    def test_empty_string_raises(self):
        with pytest.raises(StructuredOutputError):
            extract_json_object("")

    def test_none_raises(self):
        with pytest.raises(StructuredOutputError):
            extract_json_object(None)  # type: ignore


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------


class TestStructuredOutputContract:
    def test_contract_defaults(self):
        contract = StructuredOutputContract(
            name="test",
            agent_name="test_agent",
            node_name="test_node",
        )
        assert contract.name == "test"
        assert contract.max_repair_attempts == 1
        assert contract.repair_enabled is True
        assert contract.fallback_enabled is True

    def test_contract_with_model(self):
        class MyModel(BaseModel):
            field1: str
            field2: int = 0

        contract = StructuredOutputContract(
            name="test",
            agent_name="test_agent",
            node_name="test_node",
            output_model=MyModel,
        )
        assert contract.output_model is MyModel
