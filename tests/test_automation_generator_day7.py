"""
Day 7 validation: proves the classifier applies explicit, written
criteria (never arbitrary labels), matches the brief's own Section 4
examples where they apply, and that the generated automation spec is
actually executable and halts at exactly the steps it should.

Run: python -m pytest tests/test_automation_generator_day7.py -v
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from autopilot_shadow.generator.classifier import classify_workflow
from autopilot_shadow.generator.executor import AutomationExecutor
from autopilot_shadow.generator.handlers import ACTION_HANDLERS
from autopilot_shadow.mock_env.environment import MockEnvironment
from autopilot_shadow.schemas.workflow import StepType, Workflow

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def workflow():
    wf = Workflow.model_validate_json((DATA_DIR / "workflow_with_decisions.json").read_text())
    return classify_workflow(wf)


@pytest.fixture
def resumes():
    return json.loads((DATA_DIR / "resumes.json").read_text())


@pytest.fixture
def job_description():
    return json.loads((DATA_DIR / "job_description.json").read_text())


def _step(workflow, action):
    return next(s for s in workflow.steps if s.action == action)


def test_every_step_classified_with_a_reason(workflow):
    """No step is left UNCLASSIFIED or UNKNOWN risk, and every
    classification_reason is a non-empty, specific string - never blank."""
    for step in workflow.steps:
        assert step.step_type != "unclassified"
        assert step.risk != "unknown"
        assert step.classification_reason
        assert len(step.classification_reason) > 20  # not a placeholder


def test_pure_data_steps_are_automate(workflow):
    for action in ["fetch_resume", "extract_resume", "check_experience"]:
        assert _step(workflow, action).step_type == "automate"


def test_skill_matching_is_monitored_per_section_4(workflow):
    """Section 4's own table: 'Skill matching: Automatable with confidence
    monitoring' - distinct from plain AUTOMATE, and justified further by
    the Day 4/6 res_0004 synonym-mismatch finding."""
    step = _step(workflow, "compare_skills")
    assert step.step_type == "automate_with_monitoring"
    assert "Section 4" in step.classification_reason


def test_classify_candidate_is_human_review_due_to_mixed_evidence(workflow):
    step = _step(workflow, "classify_candidate")
    assert step.step_type == "human_review"
    assert "mixed" in step.classification_reason.lower()
    assert len(step.rules) == 6  # from Day 6


def test_update_candidate_record_does_not_inherit_upstream_uncertainty(workflow):
    """Deliberate design point: this step has no rules of its own, so it
    gets AUTOMATE even though the upstream classify_candidate step is
    HUMAN_REVIEW - documented in classifier.py's module docstring."""
    step = _step(workflow, "update_candidate_record")
    assert step.step_type == "automate"


def test_send_interview_invitation_is_human_review_regardless_of_rules(workflow):
    """Criterion 1 (irreversible + external-facing) fires BEFORE the
    no-rules check, so this step is human_review even with zero rules
    attached - Section 22's safety override always wins."""
    step = _step(workflow, "send_interview_invitation")
    assert step.step_type == "human_review"
    assert step.risk == "high"
    assert "Section 22" in step.classification_reason


def test_no_step_classified_blocked_in_current_dataset(workflow):
    """Honest check: BLOCKED would require ALL rules on a step to be
    UNKNOWN. classify_candidate has 2 explicit + 4 unknown (mixed), so
    it correctly lands on HUMAN_REVIEW, not BLOCKED, in this dataset."""
    assert not any(s.step_type == "blocked" for s in workflow.steps)


def test_executor_runs_automated_steps_and_halts_at_classify_candidate(workflow, resumes, job_description):
    """Full-match resume: automated steps should actually execute (fetch,
    extract, check, compare all succeed), then halt at classify_candidate
    with a PENDING approval - never silently finalizing the decision."""
    env = MockEnvironment(resumes)
    executor = AutomationExecutor(workflow, ACTION_HANDLERS)
    run_logger = executor.run(env, job_description, "res_0001")

    actions = [e.action for e in run_logger.events]
    assert actions == ["fetch_resume", "extract_resume", "check_experience", "compare_skills", "classify_candidate"]
    assert all(e.result == "success" for e in run_logger.events[:-1])
    assert run_logger.events[-1].approval == "pending"
    # never reaches update_candidate_record or email - no autonomous override of the gate
    assert "update_candidate_record" not in actions
    assert "send_interview_invitation" not in actions


def test_executor_halts_at_same_step_for_ambiguous_case(workflow, resumes, job_description):
    """res_0004 (skill synonyms, genuinely ambiguous) halts at the SAME
    step as res_0001 (clean full match) - because Section 9 classifies
    the STEP, not the individual case. This is a deliberate, documented
    scope boundary: per-instance confidence routing is Day 10/11's job,
    not Day 7's."""
    env = MockEnvironment(resumes)
    executor = AutomationExecutor(workflow, ACTION_HANDLERS)
    run_logger = executor.run(env, job_description, "res_0004")
    assert run_logger.events[-1].action == "classify_candidate"
    assert run_logger.events[-1].approval == "pending"


def test_handlers_actually_mutate_mock_environment_state(workflow, resumes, job_description):
    """Proves the executed steps are REAL mock-tool calls (S7), not stubs -
    e.g. fetch_resume actually marks the resume as processed in ResumeDatabase."""
    env = MockEnvironment(resumes)
    executor = AutomationExecutor(workflow, ACTION_HANDLERS)
    executor.run(env, job_description, "res_0001")
    assert "res_0001" in env.resume_db._processed


def test_executor_raises_on_unregistered_action():
    from autopilot_shadow.schemas.workflow import Workflow as WF

    tiny_wf = WF.model_validate(
        {
            "workflow_id": "wf_tiny",
            "workflow_name": "tiny",
            "entry_step_id": "step_1",
            "steps": [
                {"id": "step_1", "name": "mystery_action", "action": "mystery_action", "next_steps": [], "step_type": "automate"}
            ],
        }
    )
    executor = AutomationExecutor(tiny_wf, {})
    with pytest.raises(KeyError):
        executor.run(MockEnvironment([]), {"required_experience_years": 0, "required_skills": []}, "nonexistent")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
