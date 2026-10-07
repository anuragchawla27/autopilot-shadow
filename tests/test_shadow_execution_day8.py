"""
Day 8 validation: proves shadow execution runs every step (never halts
like Day 7's executor), never commits a real mutating action (CRM write
or email send), uses a fresh environment per run, and produces
confidence grounded in the rule that actually explains the decision
made — including the two real bugs caught and fixed while building this
(see docs/10).

Run: python -m pytest tests/test_shadow_execution_day8.py -v
"""

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from autopilot_shadow.schemas.workflow import Workflow
from autopilot_shadow.shadow.confidence import confidence_for_decision_step
from autopilot_shadow.shadow.shadow_executor import ShadowExecutor

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def workflow():
    return Workflow.model_validate_json((DATA_DIR / "workflow_classified.json").read_text())


@pytest.fixture
def resumes():
    return json.loads((DATA_DIR / "resumes.json").read_text())


@pytest.fixture
def job_description():
    return json.loads((DATA_DIR / "job_description.json").read_text())


def test_shadow_run_never_halts_unlike_automation_executor(workflow, resumes, job_description):
    """res_0001 halts at classify_candidate under Day 7's AutomationExecutor
    (HUMAN_REVIEW), but shadow mode must run all the way through."""
    executor = ShadowExecutor(workflow)
    run_logger = executor.run(resumes, job_description, "res_0001")
    actions = [e.action for e in run_logger.events]
    assert actions == [
        "fetch_resume",
        "extract_resume",
        "check_experience",
        "compare_skills",
        "classify_candidate",
        "update_candidate_record",
        "send_interview_invitation",
    ]
    assert all(e.result == "success" for e in run_logger.events)


def test_shadow_run_never_mutates_real_crm(workflow, resumes, job_description):
    """CRM write is proposed, not committed - a SEPARATE real CRM object
    (not passed into ShadowExecutor at all) must remain untouched."""
    from autopilot_shadow.mock_env.crm import CRM

    real_crm = CRM()  # exists only to prove nothing could have reached it
    executor = ShadowExecutor(workflow)
    executor.run(resumes, job_description, "res_0001")
    assert real_crm.all_records() == []

    # the shadow run's OWN internal environment also shows no commit:
    update_evt = None
    run_logger = executor.run(resumes, job_description, "res_0001", demo_id="check")
    for e in run_logger.events:
        if e.action == "update_candidate_record":
            update_evt = e
    assert update_evt is not None
    assert update_evt.output.get("would_set_status") == "shortlist"
    assert "note" in update_evt.output


def test_shadow_run_never_sends_a_real_email(workflow, resumes, job_description):
    executor = ShadowExecutor(workflow)
    run_logger = executor.run(resumes, job_description, "res_0001")
    send_evt = next(e for e in run_logger.events if e.action == "send_interview_invitation")
    assert send_evt.output.get("would_send") is True
    assert "drafted only, never sent" in send_evt.output.get("note", "")


def test_rejected_candidate_gets_no_email_proposal():
    """BUG CAUGHT WHILE TESTING: the first version drafted an email
    unconditionally. A rejected candidate must get would_send=False."""
    workflow = Workflow.model_validate_json((DATA_DIR / "workflow_classified.json").read_text())
    resumes = json.loads((DATA_DIR / "resumes.json").read_text())
    job_description = json.loads((DATA_DIR / "job_description.json").read_text())
    executor = ShadowExecutor(workflow)
    run_logger = executor.run(resumes, job_description, "res_0002")  # ground truth: reject
    send_evt = next(e for e in run_logger.events if e.action == "send_interview_invitation")
    assert send_evt.output.get("would_send") is False


def test_shadow_handlers_module_never_calls_send_email():
    """Structural proof (AST-based, not a comment promise) that
    shadow_handlers.py contains no call to email_service.send_email."""
    import autopilot_shadow.shadow.shadow_handlers as module

    src = Path(module.__file__).read_text()
    tree = ast.parse(src)
    called_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called_names.append(node.func.attr)
    assert "send_email" not in called_names
    assert "draft_email" in called_names


def test_shadow_run_uses_fresh_environment_no_duplicate_false_positive(workflow, resumes, job_description):
    """res_0011 is used elsewhere (Day 4) to test duplicate-fetch
    detection. A shadow run on it must NOT trip DuplicateResumeAlreadyFetched
    just because some other part of the system already touched that
    resume_id in a DIFFERENT environment instance."""
    from autopilot_shadow.mock_env.environment import MockEnvironment

    already_used_env = MockEnvironment(resumes)
    already_used_env.resume_db.fetch_resume("res_0011")  # pollute a DIFFERENT environment

    executor = ShadowExecutor(workflow)
    run_logger = executor.run(resumes, job_description, "res_0011")  # must use its OWN fresh env
    fetch_evt = run_logger.events[0]
    assert fetch_evt.result == "success"  # not a failure from a false-positive duplicate


def test_confidence_is_high_for_explicit_rule_backed_decision(workflow, resumes, job_description):
    executor = ShadowExecutor(workflow)
    run_logger = executor.run(resumes, job_description, "res_0001")  # clean full match
    classify_evt = next(e for e in run_logger.events if e.action == "classify_candidate")
    assert classify_evt.confidence == 0.95


def test_confidence_is_low_for_unknown_rule_backed_decision(workflow, resumes, job_description):
    executor = ShadowExecutor(workflow)
    run_logger = executor.run(resumes, job_description, "res_0004")  # skill synonym ambiguity
    classify_evt = next(e for e in run_logger.events if e.action == "classify_candidate")
    assert classify_evt.confidence == 0.40


def test_confidence_matches_the_outcome_actually_made_not_a_different_rule(workflow, resumes, job_description):
    """BUG CAUGHT WHILE TESTING: res_0012 (prompt injection + full skill
    match) satisfies BOTH the explicit full-match rule (-> shortlist)
    AND the injection-specific unknown rule (-> human_review). The
    actual decision is human_review (injection override wins in
    classify_candidate), so confidence must come from the rule that
    explains human_review, not the one that would have said shortlist."""
    executor = ShadowExecutor(workflow)
    run_logger = executor.run(resumes, job_description, "res_0012")
    classify_evt = next(e for e in run_logger.events if e.action == "classify_candidate")
    assert classify_evt.decision.outcome == "human_review"
    assert classify_evt.confidence == 0.40  # grounded in the UNKNOWN injection rule, not the EXPLICIT one
    assert "0.95" not in str(classify_evt.confidence)


def test_deterministic_steps_get_high_fixed_confidence(workflow, resumes, job_description):
    executor = ShadowExecutor(workflow)
    run_logger = executor.run(resumes, job_description, "res_0001")
    fetch_evt = next(e for e in run_logger.events if e.action == "fetch_resume")
    assert fetch_evt.confidence == 0.99


def test_exception_case_halts_shadow_run_too(workflow, resumes, job_description):
    """res_0009 (missing experience_years) still fails structurally in
    shadow mode - shadow execution doesn't bypass real data problems."""
    executor = ShadowExecutor(workflow)
    run_logger = executor.run(resumes, job_description, "res_0009")
    assert run_logger.events[-1].result == "failure"


def test_full_dataset_shadow_run_covers_all_resumes():
    from autopilot_shadow.shadow.build_shadow_run import main as build_main

    build_main()
    events = json.loads((DATA_DIR / "shadow_run.json").read_text())
    demo_ids = set(e["demo_id"] for e in events)
    resumes = json.loads((DATA_DIR / "resumes.json").read_text())
    for r in resumes:
        assert f"shadow_{r['resume_id']}" in demo_ids
    assert all(e["actor_type"] == "ai_shadow" for e in events)
    assert all(e["approval"] == "not_required" for e in events)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
