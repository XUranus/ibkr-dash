"""Core ReAct (Reason+Act) tool-calling runtime.

Simplified from the original LangGraph-based implementation.
Uses plain Python with ThreadPoolExecutor for parallel tool execution.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable


class AgentRuntimeError(RuntimeError):
    """Raised when a tool-calling agent cannot complete safely."""


@dataclass(frozen=True)
class AgentTool:
    """A callable tool exposed to the LLM during a ReAct loop."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any]

    def to_openai_tool(self) -> dict[str, Any]:
        """Convert this tool definition to the OpenAI function-calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ToolExecution:
    """Result of a single tool invocation."""

    tool_call_id: str
    name: str
    arguments: dict[str, Any]
    output: Any
    ok: bool
    latency_ms: int = 0


class ToolCallingRuntime:
    """ReAct loop engine: plan -> execute tools -> observe -> repeat.

    Each round calls the LLM. If the LLM requests tool calls, they are
    executed in parallel via ThreadPoolExecutor, observations are appended,
    and the loop continues. On the final round, tool calls are blocked and
    the LLM is forced to synthesize a final answer.
    """

    def __init__(
        self,
        llm_service: Any,
        *,
        max_rounds: int = 6,
        max_parallel_tools: int = 6,
        max_observation_chars: int = 12000,
        max_tokens: int | None = None,
        agent_name: str | None = None,
        call_type: str = "chat_with_tools",
    ) -> None:
        self.llm_service = llm_service
        self.max_rounds = max_rounds
        self.max_parallel_tools = max_parallel_tools
        self.max_observation_chars = max_observation_chars
        self.max_tokens = max_tokens
        self.agent_name = agent_name
        self.call_type = call_type

    def run(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[AgentTool],
        response_format: dict | None = None,
        initial_tool_calls: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Execute the ReAct loop and return {content, trace, messages}.

        Args:
            messages: Initial conversation messages.
            tools: Available tools for the LLM.
            response_format: Optional response format hint (e.g. json_object).
            initial_tool_calls: Pre-planned tool calls to execute before the
                first LLM round. Useful for default read-only data loading.

        Returns:
            Dict with keys: content, trace, messages.
        """
        trace: list[dict[str, Any]] = []
        tool_by_name = {tool.name: tool for tool in tools}
        openai_tools = [tool.to_openai_tool() for tool in tools]
        conversation = list(messages)

        # Execute pre-planned tool calls if provided
        if initial_tool_calls:
            trace.append({
                "event": "initial_tool_plan",
                "summary": "Executing default read-only tool set before LLM synthesis.",
                "created_at_ms": int(time.time() * 1000),
            })
            tool_calls = self._build_fallback_tool_calls(initial_tool_calls)
            executions = self._execute_tool_calls(tool_calls, tool_by_name, trace)
            self._append_synthetic_observations(
                conversation,
                executions,
                intro=(
                    "Below are the results of pre-executed read-only tool calls. "
                    "Please base your final strict JSON output on these results; "
                    "only call additional tools if you genuinely lack required information."
                ),
            )

        for round_index in range(1, self.max_rounds + 1):
            is_final_round = round_index == self.max_rounds

            if is_final_round:
                trace.append({
                    "event": "final_round_forced_synthesis",
                    "round": round_index,
                    "summary": "Final round: blocking tool calls, requiring strict JSON synthesis.",
                    "created_at_ms": int(time.time() * 1000),
                })
                conversation.append({
                    "role": "user",
                    "content": "This is the final round. Do not call any tools. Output strict JSON based on existing tool results only.",
                })

            # Call LLM
            started = time.perf_counter()
            trace.append({
                "event": "llm_start",
                "round": round_index,
                "created_at_ms": int(time.time() * 1000),
            })

            try:
                message = self._chat_with_optional_tools(
                    conversation=conversation,
                    openai_tools=openai_tools,
                    response_format=response_format,
                    tool_choice="none" if is_final_round else "auto",
                )
            except Exception as exc:
                if not is_final_round:
                    raise
                # Final round tool_choice=none may not be supported; try plain chat
                trace.append({
                    "event": "final_round_tool_choice_none_unsupported",
                    "round": round_index,
                    "error": str(exc)[:200],
                    "created_at_ms": int(time.time() * 1000),
                })
                message = self._synthesize_without_tools(conversation, response_format)

            trace.append({
                "event": "llm_finish",
                "round": round_index,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "created_at_ms": int(time.time() * 1000),
            })

            tool_calls = message.get("tool_calls") or []

            # Block tool calls on final round
            if tool_calls and is_final_round:
                trace.append({
                    "event": "tool_call_blocked_on_final_round",
                    "round": round_index,
                    "blocked_tool_count": len(tool_calls),
                    "created_at_ms": int(time.time() * 1000),
                })
                message = self._synthesize_without_tools(conversation, response_format)
                tool_calls = message.get("tool_calls") or []
                if tool_calls:
                    raise AgentRuntimeError("Agent final synthesis did not produce JSON")

            # No tool calls -> final answer
            if not tool_calls:
                content = str(message.get("content") or "")
                trace.append({
                    "event": "final",
                    "round": round_index,
                    "created_at_ms": int(time.time() * 1000),
                })
                return {
                    "content": content,
                    "trace": trace,
                    "messages": self._strip_reasoning_from_messages(conversation + [message]),
                }

            # Execute tool calls
            conversation.append(message)
            executions = self._execute_tool_calls(tool_calls, tool_by_name, trace)
            for execution in executions:
                conversation.append({
                    "role": "tool",
                    "tool_call_id": execution.tool_call_id,
                    "content": self._serialize_observation({
                        "ok": execution.ok,
                        "tool": execution.name,
                        "arguments": execution.arguments,
                        "data": execution.output,
                    }),
                })

        # Max rounds exhausted -> force synthesis
        return self._force_no_tools_final_answer(
            conversation=conversation,
            response_format=response_format,
            trace=trace,
        )

    # ---- LLM interaction ----

    def _chat_with_optional_tools(
        self,
        *,
        conversation: list[dict[str, Any]],
        openai_tools: list[dict[str, Any]],
        response_format: dict | None,
        tool_choice: str | dict,
    ) -> dict[str, Any]:
        if hasattr(self.llm_service, "chat_with_tools"):
            return self.llm_service.chat_with_tools(
                conversation,
                tools=openai_tools,
                temperature=None,
                max_tokens=self.max_tokens,
                response_format=response_format,
                tool_choice=tool_choice,
            )
        # Fallback: plain chat without tools
        content = self.llm_service.chat(
            conversation,
            temperature=None,
            max_tokens=self.max_tokens,
            response_format=response_format,
        )
        return {"role": "assistant", "content": content, "tool_calls": []}

    def _synthesize_without_tools(
        self,
        conversation: list[dict[str, Any]],
        response_format: dict | None,
    ) -> dict[str, Any]:
        synthesis_messages = conversation + [{
            "role": "user",
            "content": "Do not call any tools. Output only a strict JSON object based on existing observations. No Markdown.",
        }]
        content = self.llm_service.chat(
            synthesis_messages,
            temperature=None,
            max_tokens=self.max_tokens,
            response_format=response_format,
        )
        return {"role": "assistant", "content": content, "tool_calls": []}

    def _force_no_tools_final_answer(
        self,
        *,
        conversation: list[dict[str, Any]],
        response_format: dict | None,
        trace: list[dict[str, Any]],
    ) -> dict[str, Any]:
        trace.append({
            "event": "final_round_forced_synthesis",
            "summary": "Max rounds exhausted; attempting no-tools synthesis.",
            "created_at_ms": int(time.time() * 1000),
        })
        message = self._synthesize_without_tools(conversation, response_format)
        if message.get("tool_calls"):
            raise AgentRuntimeError("Agent final synthesis did not produce JSON")
        content = str(message.get("content") or "")
        trace.append({"event": "final", "round": self.max_rounds, "created_at_ms": int(time.time() * 1000)})
        return {
            "content": content,
            "trace": trace,
            "messages": self._strip_reasoning_from_messages(conversation + [message]),
        }

    # ---- Tool execution ----

    def _execute_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
        tool_by_name: dict[str, AgentTool],
        trace: list[dict[str, Any]],
    ) -> list[ToolExecution]:
        executions: list[ToolExecution] = []
        with ThreadPoolExecutor(max_workers=min(self.max_parallel_tools, max(1, len(tool_calls)))) as executor:
            future_map: dict[Any, tuple[str, str, dict[str, Any]]] = {}
            for raw_call in tool_calls:
                function = raw_call.get("function") or {}
                name = str(function.get("name") or "")
                arguments = self._parse_arguments(function.get("arguments"))
                call_id = str(raw_call.get("id") or f"tool-{len(future_map) + 1}")
                trace.append({
                    "event": "tool_start",
                    "tool_call_id": call_id,
                    "tool": name,
                    "arguments": arguments,
                    "created_at_ms": int(time.time() * 1000),
                })
                future_map[executor.submit(self._run_tool, call_id, name, arguments, tool_by_name)] = (call_id, name, arguments)

            for future in as_completed(future_map):
                started_call_id, started_name, started_args = future_map[future]
                try:
                    execution = future.result()
                except Exception as exc:
                    execution = ToolExecution(started_call_id, started_name, started_args, {"error": str(exc)}, False)
                trace.append({
                    "event": "tool_finish" if execution.ok else "tool_error",
                    "tool_call_id": execution.tool_call_id,
                    "tool": execution.name,
                    "ok": execution.ok,
                    "latency_ms": execution.latency_ms,
                    "summary": self._summarize_output(execution.output),
                    "created_at_ms": int(time.time() * 1000),
                })
                executions.append(execution)

        # Restore original order
        execution_order = {str(call.get("id") or ""): index for index, call in enumerate(tool_calls)}
        executions.sort(key=lambda item: execution_order.get(item.tool_call_id, len(execution_order)))
        return executions

    def _run_tool(
        self,
        call_id: str,
        name: str,
        arguments: dict[str, Any],
        tool_by_name: dict[str, AgentTool],
    ) -> ToolExecution:
        tool = tool_by_name.get(name)
        if tool is None:
            return ToolExecution(call_id, name, arguments, {"error": f"Unknown tool: {name}"}, False)
        started = time.perf_counter()
        try:
            output = tool.handler(**arguments)
            ok = not (isinstance(output, dict) and output.get("ok") is False)
            latency_ms = int((time.perf_counter() - started) * 1000)
            return ToolExecution(call_id, name, arguments, output, ok, latency_ms)
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return ToolExecution(call_id, name, arguments, {"error": str(exc)}, False, latency_ms)

    # ---- Helpers ----

    def _parse_arguments(self, raw_arguments: Any) -> dict[str, Any]:
        if isinstance(raw_arguments, dict):
            return raw_arguments
        if raw_arguments in (None, ""):
            return {}
        try:
            value = json.loads(str(raw_arguments))
        except json.JSONDecodeError as exc:
            raise AgentRuntimeError("Tool call arguments are not valid JSON") from exc
        if not isinstance(value, dict):
            raise AgentRuntimeError("Tool call arguments must be a JSON object")
        return value

    def _serialize_observation(self, value: Any) -> str:
        text = json.dumps(value, ensure_ascii=False, default=str)
        if len(text) <= self.max_observation_chars:
            return text
        preview_limit = max(200, self.max_observation_chars - 300)
        fallback = {
            "truncated": True,
            "reason": "observation exceeded runtime max chars",
            "original_size": len(text),
            "preview": text[:preview_limit].rstrip(),
        }
        return json.dumps(fallback, ensure_ascii=False, default=str)

    def _append_synthetic_observations(
        self,
        conversation: list[dict[str, Any]],
        executions: list[ToolExecution],
        *,
        intro: str,
    ) -> None:
        conversation.append({"role": "user", "content": intro})
        for execution in executions:
            observation = {
                "ok": execution.ok,
                "tool": execution.name,
                "arguments": execution.arguments,
                "data": execution.output,
            }
            conversation.append({
                "role": "user",
                "content": f"Tool result {execution.name}:\n{self._serialize_observation(observation)}",
            })

    def _build_fallback_tool_calls(self, calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        tool_calls = []
        for index, call in enumerate(calls, start=1):
            name = str(call.get("name") or "")
            arguments = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
            tool_calls.append({
                "id": f"fallback-{index}-{name}",
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(arguments, ensure_ascii=False),
                },
            })
        return tool_calls

    def _summarize_output(self, value: Any) -> str:
        if isinstance(value, dict):
            keys = ", ".join(list(value.keys())[:8])
            return f"object keys: {keys}" if keys else "empty object"
        if isinstance(value, list):
            return f"list length: {len(value)}"
        text = str(value)
        return text if len(text) <= 160 else text[:157].rstrip() + "..."

    @staticmethod
    def _strip_reasoning_fields(message: dict[str, Any]) -> dict[str, Any]:
        """Remove provider-private reasoning fields from an LLM response message."""
        reasoning_keys = {"reasoning_content", "thinking", "reasoning"}
        return {key: value for key, value in message.items() if key not in reasoning_keys}

    @classmethod
    def _strip_reasoning_from_messages(cls, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [cls._strip_reasoning_fields(message) if isinstance(message, dict) else message for message in messages]
