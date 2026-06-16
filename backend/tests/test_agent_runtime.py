"""End-to-end tests for ToolCallingRuntime and AgentTool.

Covers:
- AgentTool OpenAI schema conversion
- ToolCallingRuntime single-round no-tool final answer
- ToolCallingRuntime multi-round with tool calls
- ToolCallingRuntime parallel tool execution
- ToolCallingRuntime final-round forced synthesis
- ToolCallingRuntime max rounds exhaustion
- ToolCallingRuntime unknown tool handling
- ToolCallingRuntime tool error handling
- ToolCallingRuntime initial_tool_calls pre-execution
- ToolCallingRuntime observation truncation
- ToolCallingRuntime reasoning field stripping
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.agents.runtime import AgentRuntimeError, AgentTool, ToolCallingRuntime, ToolExecution


# ---- Fixtures ----

def _make_tool(name: str = "read_data", result: Any = None) -> AgentTool:
    """Create a simple test tool."""
    return AgentTool(
        name=name,
        description=f"Test tool {name}",
        parameters={"type": "object", "properties": {"query": {"type": "string"}}},
        handler=lambda query="": result or {"data": f"result_for_{query}"},
    )


def _make_llm_service(*responses: list[dict]) -> MagicMock:
    """Create a mock LLM service that returns responses in sequence."""
    service = MagicMock()
    call_count = {"n": 0}

    def chat_side_effect(*args, **kwargs):
        idx = min(call_count["n"], len(responses) - 1)
        call_count["n"] += 1
        return responses[idx].get("content", "")

    def chat_with_tools_side_effect(*args, **kwargs):
        idx = min(call_count["n"], len(responses) - 1)
        call_count["n"] += 1
        return responses[idx]

    service.chat.side_effect = chat_side_effect
    service.chat_with_tools.side_effect = chat_with_tools_side_effect
    return service


# ---- AgentTool tests ----

class TestAgentTool:
    def test_to_openai_tool_schema(self):
        tool = _make_tool("search")
        schema = tool.to_openai_tool()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "search"
        assert schema["function"]["description"] == "Test tool search"
        assert "properties" in schema["function"]["parameters"]

    def test_tool_handler_invocation(self):
        tool = _make_tool("calc", result={"value": 42})
        output = tool.handler(query="test")
        assert output == {"value": 42}

    def test_tool_frozen_dataclass(self):
        tool = _make_tool()
        with pytest.raises(AttributeError):
            tool.name = "changed"


# ---- ToolCallingRuntime tests ----

class TestToolCallingRuntime:

    def test_single_round_no_tools(self):
        """LLM returns content directly without tool calls."""
        llm = _make_llm_service({"content": '{"action": "hold"}', "tool_calls": []})
        runtime = ToolCallingRuntime(llm, max_rounds=3, agent_name="test")
        result = runtime.run(
            messages=[{"role": "user", "content": "Analyze"}],
            tools=[],
        )
        assert result["content"] == '{"action": "hold"}'
        assert any(e["event"] == "final" for e in result["trace"])

    def test_multi_round_with_tool_calls(self):
        """LLM requests a tool call, then returns final answer."""
        tool = _make_tool("get_price", result={"price": 150.0})
        llm = _make_llm_service(
            {
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "get_price",
                            "arguments": json.dumps({"query": "AAPL"}),
                        },
                    }
                ],
            },
            {"content": '{"price": 150.0}', "tool_calls": []},
        )
        runtime = ToolCallingRuntime(llm, max_rounds=3, agent_name="test")
        result = runtime.run(
            messages=[{"role": "user", "content": "Get price"}],
            tools=[tool],
        )
        assert "150.0" in result["content"]
        tool_events = [e for e in result["trace"] if e["event"] in ("tool_start", "tool_finish")]
        assert len(tool_events) >= 2

    def test_parallel_tool_execution(self):
        """Multiple tool calls in one round execute in parallel."""
        tool_a = _make_tool("tool_a", result={"a": 1})
        tool_b = _make_tool("tool_b", result={"b": 2})
        llm = _make_llm_service(
            {
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_a",
                        "type": "function",
                        "function": {"name": "tool_a", "arguments": json.dumps({"query": "a"})},
                    },
                    {
                        "id": "call_b",
                        "type": "function",
                        "function": {"name": "tool_b", "arguments": json.dumps({"query": "b"})},
                    },
                ],
            },
            {"content": '{"combined": true}', "tool_calls": []},
        )
        runtime = ToolCallingRuntime(llm, max_rounds=3, max_parallel_tools=4)
        result = runtime.run(
            messages=[{"role": "user", "content": "Run both"}],
            tools=[tool_a, tool_b],
        )
        assert "combined" in result["content"]

    def test_final_round_forced_synthesis(self):
        """On max_rounds, tool calls are blocked and synthesis is forced."""
        tool = _make_tool("fetch")
        call_count = {"n": 0}
        responses = [
            {
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "fetch", "arguments": "{}"},
                    },
                ],
            },
            {
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_2",
                        "type": "function",
                        "function": {"name": "fetch", "arguments": "{}"},
                    },
                ],
            },
            {"content": '{"final": true}', "tool_calls": []},
        ]

        llm = MagicMock()
        llm.chat_with_tools.side_effect = lambda *a, **kw: responses[min(call_count["n"], len(responses) - 1)] | (call_count.update(n=call_count["n"] + 1) or {})
        llm.chat.return_value = '{"final": true}'

        runtime = ToolCallingRuntime(llm, max_rounds=2, agent_name="test")
        result = runtime.run(
            messages=[{"role": "user", "content": "test"}],
            tools=[tool],
        )
        assert result["content"] == '{"final": true}'

    def test_unknown_tool_returns_error(self):
        """Unknown tool name produces an error execution."""
        llm = _make_llm_service(
            {
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "nonexistent_tool", "arguments": "{}"},
                    },
                ],
            },
            {"content": '{"ok": true}', "tool_calls": []},
        )
        runtime = ToolCallingRuntime(llm, max_rounds=3)
        result = runtime.run(
            messages=[{"role": "user", "content": "test"}],
            tools=[_make_tool("real_tool")],
        )
        error_events = [e for e in result["trace"] if e["event"] == "tool_error"]
        assert len(error_events) >= 1

    def test_tool_handler_exception(self):
        """Tool handler raising an exception is caught gracefully."""
        def bad_handler(**kwargs):
            raise RuntimeError("boom")

        tool = AgentTool(
            name="bad_tool",
            description="Fails",
            parameters={"type": "object", "properties": {}},
            handler=bad_handler,
        )
        llm = _make_llm_service(
            {
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "bad_tool", "arguments": "{}"},
                    },
                ],
            },
            {"content": '{"handled": true}', "tool_calls": []},
        )
        runtime = ToolCallingRuntime(llm, max_rounds=3)
        result = runtime.run(
            messages=[{"role": "user", "content": "test"}],
            tools=[tool],
        )
        error_events = [e for e in result["trace"] if e["event"] == "tool_error"]
        assert len(error_events) >= 1

    def test_initial_tool_calls_pre_execution(self):
        """Pre-planned tool calls execute before the first LLM round."""
        tool = _make_tool("load_data", result={"positions": 5})
        llm = _make_llm_service({"content": '{"loaded": true}', "tool_calls": []})
        runtime = ToolCallingRuntime(llm, max_rounds=3)
        result = runtime.run(
            messages=[{"role": "user", "content": "analyze"}],
            tools=[tool],
            initial_tool_calls=[{"name": "load_data", "arguments": {"query": "all"}}],
        )
        init_events = [e for e in result["trace"] if e["event"] == "initial_tool_plan"]
        assert len(init_events) == 1
        assert result["content"] == '{"loaded": true}'

    def test_observation_truncation(self):
        """Long tool observations are truncated."""
        huge_result = {"data": "x" * 20000}
        tool = _make_tool("big_tool", result=huge_result)
        llm = _make_llm_service(
            {
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "big_tool", "arguments": "{}"},
                    },
                ],
            },
            {"content": '{"ok": true}', "tool_calls": []},
        )
        runtime = ToolCallingRuntime(llm, max_rounds=3, max_observation_chars=500)
        result = runtime.run(
            messages=[{"role": "user", "content": "test"}],
            tools=[tool],
        )
        # Should complete without error
        assert result["content"] == '{"ok": true}'

    def test_strip_reasoning_fields(self):
        """Reasoning/thinking fields are stripped from messages."""
        messages = [
            {"role": "assistant", "content": "answer", "reasoning_content": "internal", "thinking": "deep"},
            {"role": "user", "content": "follow up"},
        ]
        stripped = ToolCallingRuntime._strip_reasoning_from_messages(messages)
        assert "reasoning_content" not in stripped[0]
        assert "thinking" not in stripped[0]
        assert stripped[0]["content"] == "answer"

    def test_max_rounds_exhausted(self):
        """When max rounds exhausted without final answer, force synthesis."""
        tool = _make_tool("loop_tool", result={"loop": True})
        call_count = {"n": 0}

        def always_tool(*args, **kwargs):
            call_count["n"] += 1
            return {
                "content": "",
                "tool_calls": [
                    {
                        "id": f"call_{call_count['n']}",
                        "type": "function",
                        "function": {"name": "loop_tool", "arguments": "{}"},
                    },
                ],
            }

        llm = MagicMock()
        llm.chat_with_tools.side_effect = always_tool
        llm.chat.return_value = '{"forced": true}'

        runtime = ToolCallingRuntime(llm, max_rounds=2)
        result = runtime.run(
            messages=[{"role": "user", "content": "loop"}],
            tools=[tool],
        )
        assert result["content"] == '{"forced": true}'

    def test_parse_arguments_dict_passthrough(self):
        """Dict arguments pass through unchanged."""
        runtime = ToolCallingRuntime(MagicMock())
        result = runtime._parse_arguments({"key": "value"})
        assert result == {"key": "value"}

    def test_parse_arguments_json_string(self):
        """JSON string arguments are parsed."""
        runtime = ToolCallingRuntime(MagicMock())
        result = runtime._parse_arguments('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_arguments_empty(self):
        """Empty/None arguments return empty dict."""
        runtime = ToolCallingRuntime(MagicMock())
        assert runtime._parse_arguments(None) == {}
        assert runtime._parse_arguments("") == {}

    def test_parse_arguments_invalid_json_raises(self):
        """Invalid JSON arguments raise AgentRuntimeError."""
        runtime = ToolCallingRuntime(MagicMock())
        with pytest.raises(AgentRuntimeError):
            runtime._parse_arguments("not json")

    def test_serialize_observation_short(self):
        """Short observations are serialized normally."""
        runtime = ToolCallingRuntime(MagicMock())
        result = runtime._serialize_observation({"key": "value"})
        assert "key" in result

    def test_serialize_observation_truncated(self):
        """Long observations are truncated with preview."""
        runtime = ToolCallingRuntime(MagicMock(), max_observation_chars=100)
        huge = {"data": "x" * 500}
        result = runtime._serialize_observation(huge)
        parsed = json.loads(result)
        assert parsed.get("truncated") is True

    def test_summarize_output_dict(self):
        """Dict output summary shows keys."""
        runtime = ToolCallingRuntime(MagicMock())
        assert "a" in runtime._summarize_output({"a": 1, "b": 2})

    def test_summarize_output_list(self):
        """List output summary shows length."""
        runtime = ToolCallingRuntime(MagicMock())
        assert "3" in runtime._summarize_output([1, 2, 3])

    def test_summarize_output_long_string(self):
        """Long string output is truncated."""
        runtime = ToolCallingRuntime(MagicMock())
        result = runtime._summarize_output("x" * 500)
        assert len(result) <= 160

    def test_build_fallback_tool_calls(self):
        """Fallback tool calls are built correctly."""
        runtime = ToolCallingRuntime(MagicMock())
        calls = runtime._build_fallback_tool_calls([
            {"name": "tool_a", "arguments": {"q": "test"}},
            {"name": "tool_b", "arguments": {}},
        ])
        assert len(calls) == 2
        assert calls[0]["function"]["name"] == "tool_a"
        assert calls[1]["id"].startswith("fallback-")

    def test_run_returns_messages(self):
        """Result includes full message history."""
        llm = _make_llm_service({"content": "hello", "tool_calls": []})
        runtime = ToolCallingRuntime(llm, max_rounds=3)
        result = runtime.run(
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
        )
        assert "messages" in result
        assert len(result["messages"]) >= 2


# ---- ToolExecution tests ----

class TestToolExecution:
    def test_tool_execution_defaults(self):
        ex = ToolExecution("id1", "tool_a", {"q": "test"}, {"data": 1}, True)
        assert ex.ok is True
        assert ex.latency_ms == 0

    def test_tool_execution_error(self):
        ex = ToolExecution("id2", "tool_b", {}, {"error": "fail"}, False, 150)
        assert ex.ok is False
        assert ex.latency_ms == 150
