"""
Day 2 validation: prove the Event and Workflow schemas actually accept
realistic data and reject bad data. This is the "proof" script for Day 2
— its output is what goes in daily_log/day02.md, not hand-typed claims.

Run: python -m pytest tests/test_schemas_day2.py -v
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from pydantic import ValidationError

from autopilot_shadow.schemas.event import (
    ActorType,
    ApprovalState,
    DecisionRecord,
    Event,
    ExceptionRecord,
    ExceptionType,
)
from autopilot_shadow.schemas.workflow import (
    Condition,
    RiskLevel,
    Rule,
    RuleType,
    StepType,
    Workflow,
    WorkflowStep,
)


def test_human_event_valid():
    """A realistic human event from the resume-screening demo (Section 5)."""
    evt = Event(
        event_id="evt_0003",
        demo_id="demo_0001",
        workflow_name="resume_screening",
        step_index=2,
        timestamp=datetime(2026, 9, 1, 10, 15, 0),
        actor="hr_reviewer_1",
        actor_type=ActorType.HUMAN,
        application="resume_parser",
        action="calculate_experience",
        input={"resume_id": "res_1042"},
        output={"experience_years": 3.5},
        decision=DecisionRecord(
            decision_name="experience_sufficiency",
            outcome="sufficient",
            evidence={"experience_years": 3.5, "required_experience": 2},
        ),
        result="success",
    )
    assert evt.actor_type == "human"
    assert evt.decision.outcome == "sufficient"


def test_ai_shadow_event_with_confidence():
    """AI shadow events (Day 8) carry confidence; human events must not."""
    evt = Event(
        event_id="evt_0003_shadow",
        demo_id="demo_0001",
        workflow_name="resume_screening",
        step_index=2,
        timestamp=datetime(2026, 9, 1, 10, 15, 1),
        actor="ai_shadow_engine",
        actor_type=ActorType.AI_SHADOW,
        application="resume_parser",
        action="calculate_experience",
        input={"resume_id": "res_1042"},
        output={"experience_years": 3.5},
        result="success",
        confidence=0.96,
    )
    assert evt.confidence == 0.96


def test_human_event_rejects_confidence():
    """Guardrail: a human event with a confidence score is a logging bug, not data."""
    with pytest.raises(ValidationError):
        Event(
            event_id="evt_bad",
            demo_id="demo_0001",
            workflow_name="resume_screening",
            step_index=0,
            timestamp=datetime.now(),
            actor="hr_reviewer_1",
            actor_type=ActorType.HUMAN,
            application="resume_parser",
            action="extract_resume",
            result="success",
            confidence=0.9,
        )


def test_event_with_exception():
    evt = Event(
        event_id="evt_0009",
        demo_id="demo_0002",
        workflow_name="resume_screening",
        step_index=1,
        timestamp=datetime.now(),
        actor="hr_reviewer_2",
        actor_type=ActorType.HUMAN,
        application="resume_parser",
        action="extract_resume",
        result="failure",
        exception=ExceptionRecord(
            exception_type=ExceptionType.MISSING_DOCUMENT,
            description="Resume PDF failed to parse - no text layer",
            recovered=False,
        ),
        approval=ApprovalState.NOT_REQUIRED,
    )
    assert evt.exception.exception_type == "missing_document"


def test_event_missing_required_field_fails():
    with pytest.raises(ValidationError):
        Event(
            event_id="evt_bad2",
            demo_id="demo_0001",
            workflow_name="resume_screening",
            step_index=0,
            timestamp=datetime.now(),
            actor="hr_reviewer_1",
            actor_type=ActorType.HUMAN,
            application="resume_parser",
            # 'action' missing on purpose
            result="success",
        )


def test_workflow_with_branch_and_rule():
    """Section 7/8: a workflow with a condition-based branch and a typed rule."""
    wf = Workflow(
        workflow_id="wf_resume_screening_v1",
        workflow_name="resume_screening",
        version=1,
        version_label="manual",
        entry_step_id="step_1",
        source_demo_ids=["demo_0001", "demo_0002"],
        steps=[
            WorkflowStep(
                id="step_1",
                name="extract_resume",
                action="extract_resume",
                application="resume_parser",
                next_steps=["step_2"],
                step_type=StepType.UNCLASSIFIED,
            ),
            WorkflowStep(
                id="step_2",
                name="eligibility_assessment",
                action="assess_eligibility",
                next_steps=["step_3a", "step_3b"],
                step_type=StepType.HUMAN_REVIEW,
                risk=RiskLevel.MEDIUM,
                classification_reason="Ambiguous cases require human judgment per Section 4",
                rules=[
                    Rule(
                        rule_id="rule_1",
                        description="IF experience>=required AND skill_present THEN shortlist ELSE human_review",
                        conditions=[
                            Condition(field="experience_years", operator=">=", value=2),
                            Condition(field="required_skill_present", operator="==", value=True),
                        ],
                        condition_logic="AND",
                        then_outcome="shortlist",
                        else_outcome="human_review",
                        rule_type=RuleType.EXPLICIT,
                    )
                ],
            ),
            WorkflowStep(id="step_3a", name="shortlist", action="shortlist_candidate", next_steps=[]),
            WorkflowStep(
                id="step_3b",
                name="human_review_queue",
                action="queue_for_review",
                next_steps=[],
                requires_approval=True,
            ),
        ],
    )
    assert wf.get_step("step_2").rules[0].rule_type == "explicit"
    assert len(wf.get_step("step_2").next_steps) == 2  # branch


def test_workflow_unknown_step_raises():
    wf = Workflow(
        workflow_id="wf_x",
        workflow_name="x",
        entry_step_id="step_1",
        steps=[WorkflowStep(id="step_1", name="a", action="a", next_steps=[])],
    )
    with pytest.raises(KeyError):
        wf.get_step("does_not_exist")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
