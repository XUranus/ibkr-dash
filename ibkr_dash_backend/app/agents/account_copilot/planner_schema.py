"""Planner action schema for Account Copilot ReAct loop.

Uses FlexibleModel with extra='allow' to handle LLM output quirks.
The model_validator coerces invalid values into safe defaults rather
than rejecting the entire output.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceSufficiency(BaseModel):
    """Whether current evidence is sufficient to answer the user."""

    model_config = ConfigDict(extra="allow")

    is_sufficient: bool = False
    missing_information: list[str] = Field(default_factory=list)
    confidence: str = "low"

    @model_validator(mode="before")
    @classmethod
    def coerce_confidence(cls, data: Any) -> Any:
        """Validate and normalise the confidence field to a known level."""
        if isinstance(data, dict):
            conf = data.get("confidence")
            if conf not in ("low", "medium", "high"):
                data["confidence"] = "low"
        return data


class CopilotPlannerAction(BaseModel):
    """Single planner action output for one ReAct round.

    Uses extra='allow' and lenient validators so that minor LLM
    deviations don't crash the planner.
    """

    model_config = ConfigDict(extra="allow")

    action_type: str = "final_answer"
    thought_summary: str = ""
    evidence_sufficiency: EvidenceSufficiency = Field(default_factory=EvidenceSufficiency)
    tool_name: str | None = None
    tool_arguments: dict = Field(default_factory=dict)
    skill_name: str | None = None
    skill_arguments: dict = Field(default_factory=dict)
    approval_message: str | None = None
    final_answer: str | None = None

    @model_validator(mode="before")
    @classmethod
    def coerce_action_type(cls, data: Any) -> Any:
        """Validate action_type, inferring it from other fields when missing."""
        if isinstance(data, dict):
            action = data.get("action_type")
            valid_actions = {"call_tool", "final_answer", "request_skill_approval"}
            if action not in valid_actions:
                # Try to infer action type from other fields
                if data.get("tool_name"):
                    data["action_type"] = "call_tool"
                elif data.get("skill_name"):
                    data["action_type"] = "request_skill_approval"
                else:
                    data["action_type"] = "final_answer"

            # Ensure evidence_sufficiency is a dict
            es = data.get("evidence_sufficiency")
            if not isinstance(es, dict):
                data["evidence_sufficiency"] = {"is_sufficient": False, "confidence": "low"}
        return data

    @model_validator(mode="after")
    def fill_missing_fields(self) -> "CopilotPlannerAction":
        """Ensure required fields are present based on action_type."""
        if self.action_type == "call_tool" and not self.tool_name:
            # If no tool name, default to final_answer
            self.action_type = "final_answer"
            if not self.final_answer:
                self.final_answer = "Unable to determine which tool to call. Please try again."

        if self.action_type == "final_answer" and not self.final_answer:
            self.final_answer = "Based on the available evidence, here is my analysis."

        if self.action_type == "request_skill_approval":
            if not self.skill_name:
                self.action_type = "final_answer"
                self.final_answer = "Unable to determine which skill to request."
            elif not self.approval_message:
                self.approval_message = f"I recommend running {self.skill_name}. Please confirm."

        return self
