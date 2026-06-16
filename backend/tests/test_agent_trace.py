"""End-to-end tests for agent run trace, trace summary, and replay snapshot.

Covers:
- AgentRunTrace dataclass and to_dict
- new_agent_run_id generation
- build_agent_run_trace from runtime artifacts
- normalize_runtime_trace_events
- extract_llm_calls_from_trace
- extract_tool_calls_from_trace
- summarize_trace_status
- sanitize_trace_payload
- build_run_trace_summary (ToolCallingRuntime + LangGraph events)
- build_replay_snapshot
- sanitize_replay_payload
- truncate_replay_payload
- summarize_large_payload
"""

from __future__ import annotations

from app.agents.agent_run_trace import (
    AgentRunTrace,
    build_agent_run_trace,
    extract_llm_calls_from_trace,
    extract_tool_calls_from_trace,
    new_agent_run_id,
    normalize_runtime_trace_events,
    sanitize_trace_payload,
    summarize_trace_status,
)
from app.agents.trace_summary import build_run_trace_summary
from app.agents.run_replay import (
    AgentReplaySnapshot,
    build_replay_snapshot,
    sanitize_replay_payload,
    truncate_replay_payload,
    summarize_large_payload,
    new_replay_id,
)


class TestAgentRunTrace:
    def test_new_agent_run_id(self):
        rid = new_agent_run_id("trade_decision")
        assert rid.startswith("trade_decision_run_")
        assert len(rid) > 20

    def test_new_agent_run_id_special_chars(self):
        rid = new_agent_run_id("My Agent!@#")
        assert "!" not in rid
        assert "@" not in rid

    def test_trace_dataclass_defaults(self):
        trace = AgentRunTrace(run_id="r1", agent_name="test")
        assert trace.final_status == "success"
        assert trace.latency_ms == 0
        assert trace.llm_calls == []
        assert trace.tool_calls == []

    def test_trace_to_dict_sanitizes(self):
        trace = AgentRunTrace(
            run_id="r1",
            agent_name="test",
            metadata={"api_key": "secret", "symbol": "AAPL"},
        )
        d = trace.to_dict()
        assert d["metadata"]["api_key"] == "***"
        assert d["metadata"]["symbol"] == "AAPL"


class TestBuildAgentRunTrace:
    def test_from_document(self):
        doc = {
            "id": "doc1",
            "symbol": "AAPL",
            "status": "success",
            "metadata": {"agent_version": "v2"},
            "run_trace": [
                {"event": "llm_start", "round": 1, "created_at_ms": 1000},
                {"event": "llm_finish", "round": 1, "latency_ms": 500, "total_tokens": 100, "created_at_ms": 1500},
                {"event": "tool_start", "tool_call_id": "t1", "tool": "get_quote", "created_at_ms": 1600},
                {"event": "tool_finish", "tool_call_id": "t1", "tool": "get_quote", "ok": True, "latency_ms": 200, "created_at_ms": 1800},
                {"event": "final", "round": 1, "created_at_ms": 2000},
            ],
        }
        trace = build_agent_run_trace(
            run_id="run_1", agent_name="trade_decision", document=doc,
        )
        assert trace.run_id == "run_1"
        assert trace.agent_name == "trade_decision"
        assert trace.agent_version == "v2"
        assert len(trace.llm_calls) >= 1
        assert len(trace.tool_calls) >= 1
        assert trace.metadata["symbol"] == "AAPL"

    def test_status_derivation_success(self):
        doc = {"status": "success"}
        trace = build_agent_run_trace(run_id="r1", agent_name="test", document=doc)
        assert trace.final_status == "success"

    def test_status_derivation_failed(self):
        doc = {}
        traces = [{"status": "failed"}]
        trace = build_agent_run_trace(run_id="r1", agent_name="test", document=doc, node_traces=traces)
        assert trace.final_status == "failed"

    def test_status_derivation_partial(self):
        doc = {"fallback_used": True}
        trace = build_agent_run_trace(run_id="r1", agent_name="test", document=doc)
        assert trace.final_status == "partial"


class TestExtractLlmCalls:
    def test_extract_from_trace(self):
        events = [
            {"event": "llm_finish", "model": "gpt-4", "total_tokens": 500, "latency_ms": 300, "ok": True},
            {"event": "llm_start"},
            {"event": "llm_finish", "model": "gpt-4", "total_tokens": 200, "latency_ms": 100, "ok": True},
        ]
        calls = extract_llm_calls_from_trace(events)
        assert len(calls) == 2
        assert calls[0]["model"] == "gpt-4"

    def test_empty_trace(self):
        assert extract_llm_calls_from_trace([]) == []


class TestExtractToolCalls:
    def test_extract_from_trace(self):
        events = [
            {"event": "tool_start", "tool_call_id": "t1", "tool": "get_quote", "arguments": {"symbol": "AAPL"}},
            {"event": "tool_finish", "tool_call_id": "t1", "tool": "get_quote", "ok": True, "latency_ms": 100},
            {"event": "tool_start", "tool_call_id": "t2", "tool": "get_news"},
            {"event": "tool_error", "tool_call_id": "t2", "tool": "get_news", "ok": False},
        ]
        calls = extract_tool_calls_from_trace(events)
        assert len(calls) == 2
        assert calls[0]["tool"] == "get_quote"
        assert calls[0]["ok"] is True
        assert calls[1]["ok"] is False


class TestSummarizeTraceStatus:
    def test_document_status(self):
        assert summarize_trace_status({"status": "success"}, []) == "success"
        assert summarize_trace_status({"status": "partial"}, []) == "partial"

    def test_node_failure(self):
        assert summarize_trace_status({}, [{"status": "failed"}]) == "failed"

    def test_fallback(self):
        assert summarize_trace_status({"fallback_used": True}, []) == "partial"

    def test_default_success(self):
        assert summarize_trace_status({}, []) == "success"


class TestSanitizeTracePayload:
    def test_redacts_sensitive_keys(self):
        data = {"api_key": "secret", "password": "pass", "symbol": "AAPL"}
        result = sanitize_trace_payload(data)
        assert result["api_key"] == "***"
        assert result["password"] == "***"
        assert result["symbol"] == "AAPL"

    def test_truncates_long_strings(self):
        data = {"text": "x" * 3000}
        result = sanitize_trace_payload(data)
        assert len(result["text"]) <= 2000

    def test_handles_nested(self):
        data = {"outer": {"inner": {"access_token": "tok123"}}}
        result = sanitize_trace_payload(data)
        assert result["outer"]["inner"]["access_token"] == "***"

    def test_handles_list(self):
        data = [{"api_key": "k"}, {"normal": "v"}]
        result = sanitize_trace_payload(data)
        assert result[0]["api_key"] == "***"
        assert result[1]["normal"] == "v"


class TestBuildRunTraceSummary:
    def test_empty_trace(self):
        summary = build_run_trace_summary([])
        assert summary["tool_call_count"] == 0
        assert summary["llm_rounds"] == 0

    def test_tool_calling_runtime_events(self):
        events = [
            {"event": "llm_start", "created_at_ms": 1000},
            {"event": "llm_finish", "created_at_ms": 1500},
            {"event": "tool_start", "tool_call_id": "t1", "tool": "get_quote"},
            {"event": "tool_finish", "tool_call_id": "t1", "tool": "get_quote", "ok": True, "summary": "got price"},
            {"event": "tool_start", "tool_call_id": "t2", "tool": "get_news"},
            {"event": "tool_error", "tool_call_id": "t2", "tool": "get_news", "summary": "timeout"},
            {"event": "final"},
        ]
        summary = build_run_trace_summary(events)
        # tool_start doesn't count, tool_finish counts as 1, tool_error counts as 1+1 (tool_start + tool_error)
        assert summary["tool_success_count"] == 1
        assert summary["tool_error_count"] >= 1
        assert summary["llm_rounds"] == 1
        assert summary["tool_call_count"] >= 2

    def test_langgraph_node_events(self):
        events = [
            {
                "event": "node_success",
                "node_name": "market_analysis",
                "tools_called": ["get_quote", "get_news"],
                "tool_call_count": 3,
                "tool_calls": [
                    {"tool_name": "get_quote", "success": True},
                    {"tool_name": "get_news", "success": True},
                    {"tool_name": "unknown_mcp_tool", "success": True},
                ],
            },
        ]
        summary = build_run_trace_summary(events)
        assert summary["tool_call_count"] == 3
        assert summary["tool_success_count"] == 3


class TestReplaySnapshot:
    def test_new_replay_id(self):
        rid = new_replay_id("trade_decision")
        assert rid.startswith("trade_decision_replay_")

    def test_build_replay_snapshot(self):
        doc = {
            "id": "doc1",
            "symbol": "AAPL",
            "status": "success",
            "metadata": {
                "agent_version": "v2",
                "agent_mode": "tool_calling",
                "prompt_metadata": {
                    "trade_decision_main": {"prompt_key": "trade_decision_main", "version": "v1"},
                },
            },
            "raw_llm_response": '{"action": "hold"}',
            "data_limitations": ["missing news"],
        }
        trace = AgentRunTrace(run_id="run_1", agent_name="trade_decision")
        snapshot = build_replay_snapshot(
            run_id="run_1",
            agent_name="trade_decision",
            request={"symbol": "AAPL"},
            document=doc,
            agent_run_trace=trace,
        )
        assert snapshot.agent_name == "trade_decision"
        assert snapshot.run_id == "run_1"
        assert snapshot.final_status == "success"
        assert "missing news" in snapshot.data_limitations

    def test_sanitize_replay_redacts_sensitive(self):
        data = {"api_key": "secret", "symbol": "AAPL"}
        result = sanitize_replay_payload(data)
        assert result["api_key"] == "***"
        assert result["symbol"] == "AAPL"

    def test_sanitize_replay_omits_system_prompt(self):
        data = {"messages": [{"role": "system", "content": "You are a helpful assistant."}]}
        result = sanitize_replay_payload(data)
        assert result["messages"][0]["content"] == "[prompt omitted]"

    def test_sanitize_replay_omits_prompt_fields(self):
        data = {"system_prompt": "secret instructions", "default_content": "hidden"}
        result = sanitize_replay_payload(data)
        assert result["system_prompt"] == "[prompt omitted]"
        assert result["default_content"] == "[prompt omitted]"

    def test_truncate_replay_payload(self):
        data = {"text": "x" * 50000}
        result = truncate_replay_payload(data, max_chars=5000)
        assert len(result["text"]) <= 5000

    def test_summarize_large_payload(self):
        data = {"key": "value"}
        summary = summarize_large_payload(data)
        assert summary["type"] == "dict"
        assert "preview" in summary

    def test_snapshot_to_dict(self):
        snapshot = AgentReplaySnapshot(
            replay_id="r1", run_id="run_1", agent_name="test",
            final_output={"api_key": "secret", "result": "ok"},
        )
        d = snapshot.to_dict()
        assert d["final_output"]["api_key"] == "***"
        assert d["final_output"]["result"] == "ok"
