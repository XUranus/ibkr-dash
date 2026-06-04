"""Account Copilot runtime: ReAct loop with tool/skill dispatch.

Simplified from the original LangGraph-based implementation.
Uses plain Python loop with structured output for planner actions.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from app.agents.account_copilot.planner_schema import CopilotPlannerAction
from app.agents.account_copilot import prompts as planner_prompts
from app.agents.account_copilot.prompts import build_planner_messages
from app.agents.account_copilot.skill_registry import AccountCopilotSkillRegistry
from app.agents.account_copilot.state import AccountCopilotState
from app.agents.account_copilot.tool_registry import AccountCopilotToolRegistry
from app.agents.prompt_runtime import resolve_runtime_prompt
from app.agents.structured_output import StructuredOutputContract, StructuredOutputRuntime
from app.utils.dates import utc_now_iso


FALLBACK_LLM_DISABLED = "Account Copilot LLM is not configured; cannot perform autonomous planning."
FALLBACK_PARSE_FAILED = "Account Copilot failed to parse planner output; stopping this round safely."
FALLBACK_MAX_ROUNDS = "Account Copilot reached maximum tool call rounds; answering with existing evidence."


class AccountCopilotRuntime:
    """ReAct loop runtime for Account Copilot.

    Each round: plan (LLM) -> execute tool/skill -> observe -> repeat.
    Supports tool calls, skill approval requests, and final answers.
    """

    def __init__(
        self,
        llm_service: Any,
        tool_registry: AccountCopilotToolRegistry,
        skill_registry: AccountCopilotSkillRegistry | None = None,
        cancel_checker: Callable[[str], bool] | None = None,
        timeout_seconds: int | None = None,
        max_rounds: int = 8,
        max_observation_chars: int = 12000,
        max_tokens: int | None = None,
        prompt_service: Any = None,
    ) -> None:
        self.llm_service = llm_service
        self.tool_registry = tool_registry
        self.skill_registry = skill_registry or AccountCopilotSkillRegistry()
        self.cancel_checker = cancel_checker
        self.timeout_seconds = timeout_seconds
        self.max_rounds = max_rounds
        self.max_observation_chars = max_observation_chars
        self.max_tokens = max_tokens
        self.prompt_service = prompt_service

    def run(self, state: AccountCopilotState) -> AccountCopilotState:
        """Execute the ReAct loop and return the final state."""
        actions: list[dict] = []
        observations: list[dict] = []
        tool_calls: list[dict] = []
        skill_requests: list[dict] = []
        errors: list[dict] = []
        planner_output: dict = {}
        pending_approval = None
        final_answer = None
        metadata: dict = {"fallback_used": False}
        started_monotonic = time.monotonic()
        consecutive_empty = 0

        for round_index in range(1, self.max_rounds + 1):
            # Check cancellation/timeout
            stop_reason = self._stop_reason(state, started_monotonic)
            if stop_reason in ("cancelled", "timeout"):
                final_answer = "This analysis has been cancelled." if stop_reason == "cancelled" else "Maximum execution time reached; stopping safely."
                metadata.update({stop_reason: True, "fallback_used": True})
                break

            # Plan
            try:
                action, raw_planner = self._plan(state, actions, observations)
            except Exception as exc:
                errors.append(self._error("PLANNER_FAILED", str(exc), round_index))
                final_answer = FALLBACK_PARSE_FAILED
                metadata["fallback_used"] = True
                break

            planner_output = raw_planner
            action_record = self._action_record(action, round_index)
            actions.append(action_record)

            # Dispatch by action_type
            if action.action_type == "final_answer":
                final_answer = action.final_answer
                break

            if action.action_type == "request_skill_approval":
                spec = self.skill_registry.get(action.skill_name)
                if spec is None or not spec.read_only or not spec.approval_required:
                    final_answer = "This skill is not available or not permitted."
                    metadata["fallback_used"] = True
                    break
                pending_approval = {
                    "skill_name": action.skill_name,
                    "skill_arguments": action.skill_arguments or {},
                    "approval_message": action.approval_message or f"I recommend running {spec.display_name}. Please confirm.",
                }
                skill_requests.append({**pending_approval, "action_id": action_record["id"], "round": round_index})
                final_answer = action.approval_message or f"I recommend running {spec.display_name}. Please confirm."
                metadata.update({"requires_approval": True})
                break

            # Execute tool
            observation, tool_call = self._execute_tool_action(action, action_record, round_index)
            observations.append(observation)
            tool_calls.append(tool_call)

            if not observation.get("ok") or not observation.get("data"):
                consecutive_empty += 1
            else:
                consecutive_empty = 0
            if consecutive_empty >= 3:
                final_answer = "Multiple consecutive tool calls returned no valid data; answering with existing evidence."
                metadata["fallback_used"] = True
                break

        if final_answer is None:
            final_answer = FALLBACK_MAX_ROUNDS
            metadata["fallback_used"] = True
            errors.append(self._error("MAX_ROUNDS_REACHED", "Max ReAct rounds reached", self.max_rounds))

        return {
            **state,
            "planner_output": planner_output,
            "actions": actions,
            "observations": observations,
            "tool_calls": tool_calls,
            "skill_requests": skill_requests,
            "pending_approval": pending_approval,
            "memory_snapshot": self._memory_snapshot(state, observations),
            "final_answer": final_answer,
            "errors": errors,
            "metadata": metadata,
        }

    def _plan(
        self,
        state: dict,
        actions: list[dict],
        observations: list[dict],
    ) -> tuple[CopilotPlannerAction, dict]:
        """Call LLM to plan the next action."""
        system_prompt, prompt_metadata = resolve_runtime_prompt(
            self.prompt_service,
            "account_copilot_planner",
            planner_prompts.SYSTEM_PROMPT,
        )
        messages = build_planner_messages(
            state, self.tool_registry, actions, observations,
            skill_registry=self.skill_registry,
            system_prompt=system_prompt,
        )
        started = time.perf_counter()
        contract = StructuredOutputContract(
            name="account_copilot_planner",
            agent_name="account_copilot",
            node_name="planner",
            output_model=CopilotPlannerAction,
            schema_hint=CopilotPlannerAction.model_json_schema(),
            examples=planner_prompts.PLANNER_ACTION_EXAMPLES,
            max_repair_attempts=1,
            repair_enabled=True,
            fallback_enabled=False,
        )
        so_runtime = StructuredOutputRuntime(self.llm_service, default_temperature=0.0, default_max_tokens=self.max_tokens)
        result = so_runtime.generate(
            messages, contract,
            temperature=0.0,
            max_tokens=self.max_tokens,
            context={"state": self._compact_planner_state(state)},
        )
        latency_ms = int((time.perf_counter() - started) * 1000)

        raw_planner = {
            "raw_action": self._safe_payload(result.payload or {}),
            "latency_ms": latency_ms,
            "repaired": result.repaired,
            "prompt_metadata": prompt_metadata,
            "structured_output": {**result.metadata, "errors": result.errors, "trace": result.trace},
        }
        if result.ok and isinstance(result.model, CopilotPlannerAction):
            return result.model, raw_planner
        error_code = result.error_code or "STRUCTURED_OUTPUT_FAILED"
        raise RuntimeError(f"Planner structured output failed: {error_code} - {result.error_message}")

    def _execute_tool_action(
        self,
        action: CopilotPlannerAction,
        action_record: dict,
        round_index: int,
    ) -> tuple[dict, dict]:
        """Execute a tool call and return (observation, tool_call_record)."""
        tool_name = action.tool_name or ""
        tool_call_id = f"tool_{uuid4().hex[:12]}"
        started = time.perf_counter()
        ok = False
        result: dict

        spec = self.tool_registry.get(tool_name)
        if spec is None:
            result = self._tool_error(tool_name, action.tool_arguments, "TOOL_NOT_FOUND", "Tool is not registered")
        elif not spec.read_only or spec.handler is None:
            result = self._tool_error(tool_name, action.tool_arguments, "TOOL_NOT_ALLOWED", "Tool is not read-only or has no handler")
        else:
            try:
                result = spec.handler(**(action.tool_arguments or {}))
                ok = bool(result.get("ok", False)) if isinstance(result, dict) else True
            except Exception as exc:
                result = self._tool_error(tool_name, action.tool_arguments, "TOOL_EXECUTION_ERROR", str(exc))

        latency_ms = int((time.perf_counter() - started) * 1000)
        observation = self._observation_from_result(action_record, round_index, tool_name, action.tool_arguments, result)
        tool_call = {
            "id": tool_call_id,
            "round": round_index,
            "tool_name": tool_name,
            "arguments": action.tool_arguments or {},
            "ok": ok,
            "latency_ms": latency_ms,
        }
        return observation, tool_call

    # ---- Helpers ----

    def _observation_from_result(
        self, action_record: dict, round_index: int,
        tool_name: str, arguments: dict, result: dict,
    ) -> dict:
        data = result.get("data") if isinstance(result, dict) else result
        limitations = list(result.get("data_limitations") or []) if isinstance(result, dict) else []
        data, truncated = self._truncate_data(data)
        if truncated:
            limitations.append("Observation was truncated by Account Copilot runtime.")
        ok = bool(result.get("ok", False)) if isinstance(result, dict) else True
        return {
            "id": f"obs_{uuid4().hex[:12]}",
            "round": round_index,
            "action_id": action_record["id"],
            "tool_name": tool_name,
            "ok": ok,
            "arguments": arguments or {},
            "data": data,
            "data_summary": self._summary(data),
            "data_limitations": limitations,
            "created_at": utc_now_iso(),
        }

    def _action_record(self, action: CopilotPlannerAction, round_index: int) -> dict:
        return {
            "id": f"act_{uuid4().hex[:12]}",
            "round": round_index,
            "action_type": action.action_type,
            "tool_name": action.tool_name,
            "tool_arguments": action.tool_arguments or {},
            "skill_name": action.skill_name,
            "skill_arguments": action.skill_arguments or {},
            "thought_summary": action.thought_summary,
            "evidence_sufficiency": action.evidence_sufficiency.model_dump(),
            "created_at": utc_now_iso(),
        }

    def _tool_error(self, tool_name: str, arguments: dict, error_code: str, message: str) -> dict:
        return {
            "ok": False,
            "tool": tool_name,
            "arguments": arguments or {},
            "data": {},
            "data_source": "ACCOUNT_COPILOT_RUNTIME",
            "data_limitations": [message],
            "metadata": {"error_code": error_code, "message": message},
        }

    def _truncate_data(self, data: Any) -> tuple[Any, bool]:
        text = json.dumps(data, ensure_ascii=False, default=str)
        if len(text) <= self.max_observation_chars:
            return data, False
        return {"truncated_json": text[:self.max_observation_chars]}, True

    def _summary(self, data: Any) -> str:
        if isinstance(data, dict):
            return f"object keys={list(data.keys())[:8]}"
        if isinstance(data, list):
            return f"list length={len(data)}"
        return str(data)[:160]

    def _safe_payload(self, payload: dict) -> dict:
        return {key: value for key, value in payload.items() if key not in {"reasoning", "thinking", "chain_of_thought"}}

    def _compact_planner_state(self, state: dict) -> dict:
        return {
            "session_id": state.get("session_id"),
            "run_id": state.get("run_id"),
            "user_input": state.get("user_input"),
            "message_count": len(state.get("messages") or []),
            "memory_keys": list((state.get("memory_snapshot") or {}).keys())[:10],
        }

    def _memory_snapshot(self, state: dict, observations: list[dict]) -> dict:
        existing = dict(state.get("memory_snapshot") or {})
        return {
            **existing,
            "session_id": state.get("session_id"),
            "rolling_summary": state.get("rolling_summary") or "",
            "pinned_facts": state.get("pinned_facts") or {},
            "observation_count": len(observations),
        }

    def _error(self, code: str, message: str, round_index: int) -> dict:
        return {"code": code, "message": message[:500], "round": round_index, "created_at": utc_now_iso()}

    def _stop_reason(self, state: dict, started_monotonic: float) -> str | None:
        run_id = state.get("run_id")
        if run_id and self.cancel_checker is not None and self.cancel_checker(str(run_id)):
            return "cancelled"
        if self.timeout_seconds is not None and time.monotonic() - started_monotonic >= self.timeout_seconds:
            return "timeout"
        return None
