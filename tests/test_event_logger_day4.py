"""
Day 4 validation: proves the event logger correctly turns mock-environment
calls into Day 2 Events for both successful and failing steps, and that
the human demo policy produces the expected classification for every
synthetic resume against data/ground_truth.json.

Run: python -m pytest tests/test_event_logger_day4.py -v
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from autopilot_shadow.logger.human_demo import run_human_demo
from autopilot_shadow.mock_env.environment import MockEnvironment
from autopilot_shadow.mock_env.faults import FaultType

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def resumes():
    return json.loads((DATA_DIR / "resumes.json").read_text())


@pytest.fixture
def job_description():
    return json.loads((DATA_DIR / "job_description.json").read_text())


@pytest.fixture
def ground_truth():
    return json.loads((DATA_DIR / "ground_truth.json").read_text())["labels"]


def _classification_of(logger):
    """Pull the final classify_candidate decision outcome out of a demo's events."""
    for evt in logger.events:
        if evt.action == "classify_candidate" and evt.decision is not None:
            return evt.decision.outcome
    return None


@pytest.mark.parametrize(
    "resume_id",
    ["res_0001", "res_0002", "res_0003", "res_0004", "res_0005", "res_0006", "res_0007", "res_0008", "res_0011", "res_0012"],
)
def test_human_demo_matches_ground_truth(resumes, job_description, ground_truth, resume_id):
    env = MockEnvironment(resumes)
    logger = run_human_demo(env, job_description, resume_id)
    classification = _classification_of(logger)
    expected = ground_truth[resume_id]["expected_decision"]
    assert classification == expected, f"{resume_id}: got {classification!r}, expected {expected!r}"


def test_demo_stops_early_on_missing_information(resumes, job_description):
    """res_0009 has an empty experience_years -> parse fails structurally,
    no classify_candidate step should ever run."""
    env = MockEnvironment(resumes)
    logger = run_human_demo(env, job_description, "res_0009")
    actions = [e.action for e in logger.events]
    assert "classify_candidate" not in actions
    assert logger.events[-1].result == "failure"
    assert logger.events[-1].exception is not None


def test_demo_stops_early_on_malformed_skills(resumes, job_description):
    env = MockEnvironment(resumes)
    logger = run_human_demo(env, job_description, "res_0010")
    actions = [e.action for e in logger.events]
    assert "classify_candidate" not in actions
    assert logger.events[-1].result == "failure"


def test_shortlisted_candidate_gets_email_sent(resumes, job_description):
    env = MockEnvironment(resumes)
    logger = run_human_demo(env, job_description, "res_0001")
    assert _classification_of(logger) == "shortlist"
    email_events = [e for e in logger.events if e.action == "send_interview_invitation"]
    assert len(email_events) == 1
    assert email_events[0].result == "success"
    assert len(env.email_service.outbox) == 1


def test_rejected_candidate_gets_no_email(resumes, job_description):
    env = MockEnvironment(resumes)
    logger = run_human_demo(env, job_description, "res_0002")
    assert _classification_of(logger) == "reject"
    email_events = [e for e in logger.events if e.action == "send_interview_invitation"]
    assert len(email_events) == 0
    assert env.email_service.outbox == []


def test_events_are_ordered_and_share_demo_id(resumes, job_description):
    env = MockEnvironment(resumes)
    logger = run_human_demo(env, job_description, "res_0001", demo_id="demo_test_order")
    step_indices = [e.step_index for e in logger.events]
    assert step_indices == sorted(step_indices)
    assert all(e.demo_id == "demo_test_order" for e in logger.events)


def test_injected_tool_failure_on_fetch_is_logged_not_raised(resumes, job_description):
    """The logger must catch mock-tool errors and record them as Events,
    never let them propagate and crash demo generation."""
    env = MockEnvironment(resumes)
    logger = run_human_demo(env, job_description, "res_0001", fault_on_fetch=FaultType.TOOL_FAILURE)
    assert logger.events[0].result == "failure"
    assert logger.events[0].exception.exception_type == "tool_failure"
    assert len(logger.events) == 1  # stopped after the failed fetch


def test_prompt_injection_resume_forced_to_human_review(resumes, job_description, ground_truth):
    env = MockEnvironment(resumes)
    logger = run_human_demo(env, job_description, "res_0012")
    classify_evt = [e for e in logger.events if e.action == "classify_candidate"][0]
    assert classify_evt.decision.outcome == "human_review"
    assert "injection" in classify_evt.reasoning_summary.lower()


def test_full_dataset_builds_and_covers_all_resumes(resumes):
    from autopilot_shadow.logger.build_dataset import build_all_demonstrations

    events = build_all_demonstrations()
    demo_ids = set(e["demo_id"] for e in events)
    assert len(events) > 0
    # every plain per-resume demo id is present
    for r in resumes:
        assert any(r["resume_id"] in d for d in demo_ids)
    # duplicate + fault demos are present
    assert any(d.startswith("demo_dup_") for d in demo_ids)
    assert any(d.startswith("demo_fault_") for d in demo_ids)
    # every event is JSON-serializable (already dicts here) and has required keys
    for e in events:
        assert "event_id" in e and "demo_id" in e and "action" in e and "result" in e


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
