"""Planner action schema for Account Copilot ReAct loop."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class EvidenceSufficiency(BaseModel):
    """Whether current evidence is sufficient to answer the user."""

    is_sufficient: bool
    missing_information: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"]


class CopilotPlannerAction(BaseModel):
    """Single planner action output for one ReAct round."""

    action_type: Literal["call_tool", "final_answer", "request_skill_approval"]
    thought_summary: str
    evidence_sufficiency: EvidenceSufficiency
    tool_name: str | None = None
    tool_arguments: dict = Field(default_factory=dict)
    skill_name: str | None = None
    skill_arguments: dict = Field(default_factory=dict)
    approval_message: str | None = None
    final_answer: str | None = None

    @model_validator(mode="after")
    def validate_action_payload(self) -> "CopilotPlannerAction":
        if self.action_type == "call_tool" and not self.tool_name:
            raise ValueError("tool_name is required when action_type is call_tool")
        if self.action_type == "final_answer" and not self.final_answer:
            raise ValueError("final_answer is required when action_type is final_answer")
        if self.action_type == "request_skill_approval":
            if not self.skill_name:
                raise ValueError("skill_name is required when action_type is request_skill_approval")
            if not self.approval_message:
                raise ValueError("approval_message is required when action_type is request_skill_approval")
        return self
