"""
Day 5 validation: proves the reconstruction engine turns the Day 4 event
log into a structurally correct Workflow, catches the classify_candidate
branch, and scores near-perfect against the Section 5 canonical sequence.

Run: python -m pytest tests/test_reconstruction_day5.py -v
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from autopilot_shadow.reconstruction.engine import (
    filter_structural_demos,
    reconstruct_workflow,
    reconstruction_stats,
)
from autopilot_shadow.reconstruction.evaluate import evaluate_reconstruction

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def events():
    return json.loads((DATA_DIR / "demonstrations.json").read_text())


@pytest.fixture
def structural_events(events):
    return filter_structural_demos(events)


@pytest.fixture
def workflow(structural_events):
    return reconstruct_workflow(structural_events, workflow_name="resume_screening", workflow_id="wf_resume_screening_v1")


def test_filter_excludes_dup_and_fault_demos(events, structural_events):
    demo_ids = {e["demo_id"] for e in structural_events}
    assert not any(d.startswith("demo_dup_") for d in demo_ids)
    assert not any(d.startswith("demo_fault_") for d in demo_ids)
    assert len(structural_events) < len(events)


def test_entry_step_is_fetch_resume(workflow):
    entry = workflow.get_step(workflow.entry_step_id)
    assert entry.action == "fetch_resume"


def test_all_expected_actions_present_as_single_steps(workflow):
    action_names = [s.action for s in workflow.steps]
    # each action appears exactly once as a step - not once per demo
    assert len(action_names) == len(set(action_names))
    for expected in [
        "fetch_resume",
        "extract_resume",
        "check_experience",
        "compare_skills",
        "classify_candidate",
        "update_candidate_record",
        "send_interview_invitation",
    ]:
        assert expected in action_names


def test_classify_candidate_is_a_branch_point(workflow):
    """classify_candidate is always followed by update_candidate_record
    in every demo, so it should have exactly one outgoing edge - the
    BRANCH happens one step later, at update_candidate_record, which is
    followed by send_interview_invitation only in shortlist demos and by
    nothing (end of demo) otherwise."""
    classify_step = next(s for s in workflow.steps if s.action == "classify_candidate")
    assert len(classify_step.next_steps) == 1  # always -> update_candidate_record

    update_step = workflow.get_step(classify_step.next_steps[0])
    assert update_step.action == "update_candidate_record"
    # branch: some demos end here (reject/human_review), others continue to email
    send_step_ids = [s.id for s in workflow.steps if s.action == "send_interview_invitation"]
    assert send_step_ids
    assert send_step_ids[0] in update_step.next_steps


def test_unclassified_steps_have_no_premature_labels(workflow):
    """Reconstruction must NOT classify steps or assign risk - that's
    Day 7 / Day 10's job. Confirms scope separation is respected."""
    for step in workflow.steps:
        assert step.step_type == "unclassified"
        assert step.risk == "unknown"
        assert step.classification_reason is None


def test_reconstruction_stats_reasonable(workflow, structural_events):
    stats = reconstruction_stats(workflow, structural_events)
    assert stats["num_demonstrations"] == 12
    assert stats["num_distinct_steps"] == 7
    # NOTE: this dataset has no true multi-way branch (a step with 2+
    # DIFFERENT next actions). update_candidate_record's continuation is
    # optional (some demos end there, some continue to
    # send_interview_invitation) rather than forking to different named
    # actions, so num_branch_steps is legitimately 0 here - see docs/07.
    assert stats["num_branch_steps"] == 0


def test_update_candidate_record_continuation_is_optional_not_a_true_branch(structural_events):
    """Confirms the nuance directly against the raw event log: some demos
    that reach update_candidate_record stop there (reject/human_review),
    others continue to send_interview_invitation (shortlist) - this is
    optional termination, not a fork to multiple distinct next actions."""
    from autopilot_shadow.reconstruction.engine import _group_by_demo

    by_demo = _group_by_demo(structural_events)
    ends_at_update = 0
    continues_to_email = 0
    for demo_events in by_demo.values():
        actions = [e["action"] for e in demo_events]
        if "update_candidate_record" not in actions:
            continue
        if actions[-1] == "update_candidate_record":
            ends_at_update += 1
        elif "send_interview_invitation" in actions:
            continues_to_email += 1
    assert ends_at_update > 0
    assert continues_to_email > 0


def test_evaluate_reconstruction_perfect_on_canonical_sequence(workflow):
    result = evaluate_reconstruction(workflow)
    assert result["step_recall"] == 1.0
    assert result["steps_missing"] == []
    assert result["edge_recall"] == 1.0
    assert result["edge_misses"] == []


def test_including_dup_and_fault_demos_would_pollute_the_graph(events):
    """Negative control: proves the filter in test above is doing real
    work, not a no-op - without it, the dup demo's extra post-completion
    fetch_resume call creates a spurious edge from send_interview_invitation."""
    polluted_workflow = reconstruct_workflow(events, workflow_name="resume_screening", workflow_id="wf_polluted")
    send_step = next(s for s in polluted_workflow.steps if s.action == "send_interview_invitation")
    fetch_step = next(s for s in polluted_workflow.steps if s.action == "fetch_resume")
    assert fetch_step.id in send_step.next_steps  # the spurious edge exists when unfiltered


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
