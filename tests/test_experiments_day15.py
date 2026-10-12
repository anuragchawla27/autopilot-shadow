"""
Day 15 validation: Experiments A-E (Section 30), run against the real
12-resume dataset, plus unit tests for the shared metric aggregation.

Run: python -m pytest tests/test_experiments_day15.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from autopilot_shadow.experiments import engine
from autopilot_shadow.experiments.case_outcome import CaseOutcome, aggregate


def _outcome(resume_id, expected, final, automated, halted, failed, would_send, steps, matches):
    return CaseOutcome(
        resume_id=resume_id,
        expected_decision=expected,
        final_action=final,
        automated=automated,
        halted_for_human=halted,
        failed=failed,
        would_send_invitation=would_send,
        steps_executed=steps,
        matches_ground_truth=matches,
    )


# --- aggregate() unit tests -------------------------------------------------

def test_aggregate_rejects_empty_list():
    with pytest.raises(ValueError):
        aggregate([])


def test_aggregate_computes_coverage_and_interventions():
    outcomes = [
        _outcome("r1", "shortlist", "shortlist", True, False, False, True, 7, True),
        _outcome("r2", "reject", None, False, True, False, False, 5, None),
    ]
    agg = aggregate(outcomes)
    assert agg["n_cases"] == 2
    assert agg["automation_coverage_pct"] == 50.0
    assert agg["human_interventions_pct"] == 50.0


def test_aggregate_unsafe_send_judged_against_final_action_not_ground_truth():
    # Classification was CORRECT (matches ground truth) but an invitation
    # still went out for a non-shortlist case — the orchestration defect
    # this metric exists to catch, independent of classification accuracy.
    outcomes = [_outcome("r1", "reject", "reject", True, False, False, True, 7, True)]
    agg = aggregate(outcomes)
    assert agg["unsafe_invitations_sent"] == 1


def test_aggregate_false_automation_requires_both_automated_and_wrong():
    outcomes = [
        _outcome("r1", "shortlist", "reject", True, False, False, False, 7, False),  # automated + wrong
        _outcome("r2", "shortlist", "reject", False, True, False, False, 3, False),  # wrong but halted, not automated
    ]
    agg = aggregate(outcomes)
    assert agg["false_automation"] == 1
    assert agg["errors"] == 2


# --- real-data experiments ---------------------------------------------------

def test_experiment_a_is_fully_manual():
    result = engine.run_experiment_a()
    m = result["metrics"]
    assert m["automation_coverage_pct"] == 0.0
    assert m["human_interventions_pct"] == 100.0
    assert m["unsafe_invitations_sent"] == 0


def test_experiment_b_naive_executor_demonstrates_the_real_danger():
    """This is the whole point of Experiment B (Section 1's own warning):
    with no gate between classification and communication, the real
    handler drafts an invitation regardless of the decision it just made."""
    result = engine.run_experiment_b()
    m = result["metrics"]
    assert m["automation_coverage_pct"] > 0
    assert m["unsafe_invitations_sent"] > 0, (
        "Experiment B is expected to show unsafe sends — if this ever reads 0, "
        "the naive executor stopped being naive, or send_interview_invitation's "
        "handler started checking classification (which would mean Section 22's "
        "hard override is implemented at the wrong layer — verify before 'fixing' this test)."
    )


def test_experiment_c_halts_before_classification_every_case():
    result = engine.run_experiment_c()
    m = result["metrics"]
    assert m["unsafe_invitations_sent"] == 0
    assert m["automation_coverage_pct"] == 0.0  # Day 7's step-level classification halts everyone identically


def test_experiment_d_confidence_only_is_safer_than_naive_but_not_safe():
    exp_b = engine.run_experiment_b()["metrics"]
    exp_d = engine.run_experiment_d()["metrics"]
    assert 0 < exp_d["unsafe_invitations_sent"] < exp_b["unsafe_invitations_sent"], (
        "Experiment D should sit strictly between B (unsafe) and E (0 unsafe) — "
        "it catches the low-confidence cases but not the hard-override gap."
    )


def test_experiment_e_full_risk_aware_system_has_zero_unsafe_sends():
    """The real point of E: Section 22's hard override is checked BEFORE the
    action runs, not after — this is what actually gets unsafe sends to 0,
    not luck. See risk_aware_executor.py's module docstring for the bug this
    test guards against (an earlier version scored AFTER running)."""
    result = engine.run_experiment_e()
    m = result["metrics"]
    assert m["unsafe_invitations_sent"] == 0


def test_experiment_e_gets_further_per_case_than_experiment_c():
    """E's case-by-case risk scoring should let clean cases progress further
    (through classify_candidate and update_candidate_record) than C's blunt
    step-level halt, even though both correctly stop before the hard-override
    action — this is the actual value Day 10's risk model adds over Day 7's
    classification alone."""
    exp_c = engine.run_experiment_c()["metrics"]
    exp_e = engine.run_experiment_e()["metrics"]
    assert exp_e["avg_steps_executed"] > exp_c["avg_steps_executed"]


def test_run_all_returns_five_experiments_in_order():
    results = engine.run_all()
    assert [r["experiment"] for r in results] == ["A", "B", "C", "D", "E"]
    for r in results:
        assert r["metrics"]["n_cases"] == 12
