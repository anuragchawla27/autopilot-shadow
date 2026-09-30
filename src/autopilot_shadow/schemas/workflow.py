"""
Workflow schema — the structured representation a set of Events gets
turned into (Day 5), and the thing the automation generator (Day 7)
converts into something executable.

Per Section 7 of the brief, the representation must support: sequential
steps, branching, conditions, loops, exceptions, human approvals, tool
calls, and outputs. This module covers all of those explicitly rather
than leaving them implicit in free text.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class StepType(str, Enum):
    """Brief's automation-candidate categories (Section 9). Assigned by
    the automation generator (Day 7) using explicit criteria — never
    guessed at reconstruction time."""

    AUTOMATE = "automate"
    AUTOMATE_WITH_MONITORING = "automate_with_monitoring"
    HUMAN_REVIEW = "human_review"
    HUMAN_ONLY = "human_only"
    BLOCKED = "blocked"
    UNCLASSIFIED = "unclassified"  # default at reconstruction time, Day 5


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class RuleType(str, Enum):
    """Section 8 — mandatory three-way distinction."""

    EXPLICIT = "explicit"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class Condition(BaseModel):
    """A single branch condition, e.g. 'experience_years >= required_experience'.

    Kept as structured (field, operator, value) rather than a raw string
    so the decision-extraction engine (Day 6) and the automation generator
    (Day 7) can both evaluate it programmatically.
    """

    field: str
    operator: str = Field(..., description="One of: >=, <=, ==, !=, >, <, in, contains")
    value: object


class Rule(BaseModel):
    """A decision rule attached to a step, per Section 8."""

    rule_id: str
    description: str = Field(..., description="Human-readable form, e.g. 'IF experience>=req AND skill_present THEN shortlist'")
    conditions: list[Condition] = Field(default_factory=list)
    condition_logic: str = Field(default="AND", description="AND | OR")
    then_outcome: str
    else_outcome: Optional[str] = None
    rule_type: RuleType
    evidence_count: int = Field(default=0, description="Number of demonstrations supporting this rule (for inferred rules)")
    source_demo_ids: list[str] = Field(default_factory=list)


class ExceptionHandler(BaseModel):
    """Per Section 17 — how a step reacts to a named exception condition."""

    exception_type: str
    trigger_condition: str = Field(..., description="e.g. 'confidence < threshold', 'required_data_missing'")
    action: str = Field(default="human_review", description="What happens when this exception fires")


class WorkflowStep(BaseModel):
    """One node in the reconstructed workflow graph."""

    id: str = Field(..., description="e.g. 'step_1'")
    name: str = Field(..., description="e.g. 'extract_resume'")
    description: str = ""

    # graph structure — supports sequences and branching
    next_steps: list[str] = Field(
        default_factory=list, description="IDs of steps that follow. >1 entry means a branch."
    )
    loop_back_to: Optional[str] = Field(
        default=None, description="Step ID this step can loop back to, if any (Section 7: loops)"
    )

    # tool / action
    application: Optional[str] = Field(default=None, description="Tool this step calls, e.g. 'resume_db'")
    action: str = Field(..., description="e.g. 'extract_resume'")

    # classification (filled progressively across days)
    step_type: StepType = StepType.UNCLASSIFIED
    risk: RiskLevel = RiskLevel.UNKNOWN
    classification_reason: Optional[str] = Field(
        default=None, description="Explicit justification for step_type — required, never arbitrary (Section 9)"
    )

    # decisions and exceptions attached to this step
    rules: list[Rule] = Field(default_factory=list)
    exception_handlers: list[ExceptionHandler] = Field(default_factory=list)

    # human-in-the-loop
    requires_approval: bool = Field(default=False, description="Section 18 — explicit approval gate")

    # outputs
    outputs: list[str] = Field(default_factory=list, description="Named outputs this step produces")


class Workflow(BaseModel):
    """A full reconstructed (or hand-authored) workflow."""

    workflow_id: str
    workflow_name: str = Field(..., description="e.g. 'resume_screening'")
    version: int = Field(default=1, description="Section 25 — workflow versioning")
    version_label: Optional[str] = Field(
        default=None, description="e.g. 'manual', 'partially_automated', 'human_in_the_loop', 'high_confidence'"
    )
    entry_step_id: str
    steps: list[WorkflowStep]

    source_demo_ids: list[str] = Field(
        default_factory=list, description="Which demonstrations this reconstruction was built from"
    )

    def get_step(self, step_id: str) -> WorkflowStep:
        for s in self.steps:
            if s.id == step_id:
                return s
        raise KeyError(f"No step with id {step_id!r} in workflow {self.workflow_id!r}")
