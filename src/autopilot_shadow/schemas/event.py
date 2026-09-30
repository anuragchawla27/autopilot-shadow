"""
Event schema — the atomic unit of everything this system observes.

Every action a human (or later, the AI) performs while executing the
workflow is captured as one Event. A workflow demonstration is just an
ordered list of Events sharing a demo_id. The reconstruction engine
(Day 5) reads nothing but lists of these.

Design notes:
- Fields follow the brief's list exactly: timestamp, actor, application/tool,
  action, input, output, decision, reasoning summary, result, exception,
  approval.
- `actor_type` distinguishes human-recorded events from AI-shadow-produced
  events, because both will eventually live in the same store and get
  compared (Day 9).
- `decision` and `exception` are optional structured sub-objects rather than
  free text, so downstream rule-extraction (Day 6) can rely on typed fields
  instead of parsing prose.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class ActorType(str, Enum):
    HUMAN = "human"
    AI_SHADOW = "ai_shadow"
    SYSTEM = "system"


class ExceptionType(str, Enum):
    """Matches Section 17 / 23 of the brief."""

    MISSING_DOCUMENT = "missing_document"
    INVALID_INPUT = "invalid_input"
    CONFLICTING_INFORMATION = "conflicting_information"
    DUPLICATE_RECORD = "duplicate_record"
    API_UNAVAILABLE = "api_unavailable"
    UNEXPECTED_FORMAT = "unexpected_format"
    AMBIGUOUS_DECISION = "ambiguous_decision"
    TOOL_FAILURE = "tool_failure"
    OTHER = "other"


class ApprovalState(str, Enum):
    """Section 18 — human-in-the-loop gate outcomes. NOT_REQUIRED covers
    steps that never reach a gate (e.g. plain data extraction)."""

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class DecisionRecord(BaseModel):
    """Captures a single decision point taken during this event, if any.

    `rule_type` is deliberately left for the decision-extraction engine
    (Day 6) to fill in later — at logging time we only know WHAT was
    decided, not yet whether the rule behind it is explicit / inferred /
    unknown. It defaults to None here for that reason.
    """

    decision_name: str = Field(..., description="e.g. 'eligibility_assessment'")
    outcome: str = Field(..., description="e.g. 'shortlist', 'reject', 'human_review'")
    rule_type: Optional[str] = Field(
        default=None,
        description="explicit | inferred | unknown — set later by decision extraction, not at logging time",
    )
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Facts the decision was based on, e.g. {'experience_years': 3, 'required_experience': 2}",
    )


class ExceptionRecord(BaseModel):
    exception_type: ExceptionType
    description: str
    recovered: bool = Field(
        default=False, description="Whether the workflow continued after this exception, vs. halted."
    )


class Event(BaseModel):
    """One atomic step in a workflow demonstration."""

    # --- identity -----------------------------------------------------
    event_id: str = Field(..., description="Unique id, e.g. UUID or 'evt_0001'")
    demo_id: str = Field(..., description="Groups events into one end-to-end workflow run")
    workflow_name: str = Field(..., description="e.g. 'resume_screening'")
    step_index: int = Field(..., ge=0, description="Order of this event within the demo, starting at 0")

    # --- required brief fields -----------------------------------------
    timestamp: datetime
    actor: str = Field(..., description="e.g. 'hr_reviewer_1', 'ai_shadow_engine'")
    actor_type: ActorType
    application: str = Field(..., description="Tool/app used, e.g. 'resume_db', 'crm', 'email_service'")
    action: str = Field(..., description="e.g. 'extract_resume', 'shortlist_candidate'")
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    decision: Optional[DecisionRecord] = None
    reasoning_summary: Optional[str] = Field(
        default=None, description="Short human- or AI-authored rationale, where legitimately available"
    )
    result: str = Field(..., description="e.g. 'success', 'failure', 'partial'")
    exception: Optional[ExceptionRecord] = None
    approval: ApprovalState = ApprovalState.NOT_REQUIRED

    # --- shadow-mode / risk fields (used from Day 8 onward) ------------
    confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="AI confidence in this action, 0-1. Null for human events."
    )
    reversible: Optional[bool] = Field(
        default=None, description="Whether this action can be undone. Filled by the risk model, Day 10."
    )

    @field_validator("confidence")
    @classmethod
    def confidence_only_for_ai(cls, v, info):
        actor_type = info.data.get("actor_type")
        if v is not None and actor_type == ActorType.HUMAN:
            raise ValueError("Human events should not carry a confidence score.")
        return v

    model_config = {
        "use_enum_values": True,
        "json_schema_extra": {
            "description": "Atomic workflow event. See docs/04_event_schema.md for the full spec."
        },
    }
