"""
Day 12 validation: correction memory storage/retrieval (Section 24) and
workflow versioning/diffing (Section 25), including the honest
simulated-vs-real distinction in the correction memory's real-data run.

Run: python -m pytest tests/test_correction_versioning_day12.py -v
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from autopilot_shadow.correction.build_correction_memory import simulate_decision
from autopilot_shadow.correction.from_approval import correction_from_outcome
from autopilot_shadow.correction.memory import CorrectionMemory
from autopilot_shadow.correction.schema import CorrectionRecord, now_iso
from autopilot_shadow.exceptions.approval_gate import ApprovalRequest, apply_decision
from autopilot_shadow.versioning.version_diff import diff, diff_all_consecutive
from autopilot_shadow.versioning.workflow_version import WorkflowVersion, build_versions

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"


def _record(correction_id="corr_1", action="classify_candidate", ts="2026-01-01T00:00:00+00:00"):
    return CorrectionRecord(
        correction_id=correction_id,
        workflow_context={"workflow": "resume_screening", "resume_id": "res_x", "action": action},
        original_ai_decision={"recommendation": "automate_with_monitoring", "risk_score": 0.3, "reason": "x"},
        human_correction="edit",
        human_correction_detail={"approval_state": "edited", "edited_payload": {"note": "x"}, "note": "x"},
        evidence={"recommendation_that_was_overridden": "automate_with_monitoring", "risk_score": 0.3},
        reason="test",
        timestamp=ts,
        source="human_review",
    )


# --- memory.py -------------------------------------------------------

def test_add_and_retrieve_by_action():
    mem = CorrectionMemory()
    mem.add(_record("c1", action="classify_candidate"))
    mem.add(_record("c2", action="fetch_resume"))
    assert len(mem.for_action("classify_candidate")) == 1
    assert len(mem.for_action("fetch_resume")) == 1
    assert len(mem.for_action("nonexistent_action")) == 0


def test_retrieve_similar_orders_most_recent_first():
    mem = CorrectionMemory()
    mem.add(_record("old", action="classify_candidate", ts="2026-01-01T00:00:00+00:00"))
    mem.add(_record("new", action="classify_candidate", ts="2026-06-01T00:00:00+00:00"))
    results = mem.retrieve_similar("classify_candidate")
    assert [r.correction_id for r in results] == ["new", "old"]


def test_retrieve_similar_respects_top_n():
    mem = CorrectionMemory()
    for i in range(10):
        mem.add(_record(f"c{i}", action="classify_candidate", ts=f"2026-01-{i+1:02d}T00:00:00+00:00"))
    assert len(mem.retrieve_similar("classify_candidate", top_n=3)) == 3


def test_correction_rate_by_action():
    mem = CorrectionMemory()
    mem.add(_record("c1", action="classify_candidate"))
    mem.add(_record("c2", action="classify_candidate"))
    mem.add(_record("c3", action="fetch_resume"))
    rates = mem.correction_rate_by_action()
    assert rates["classify_candidate"]["correction_count"] == 2
    assert rates["fetch_resume"]["correction_count"] == 1


def test_save_and_load_roundtrip(tmp_path):
    mem = CorrectionMemory()
    mem.add(_record("c1"))
    path = tmp_path / "mem.json"
    mem.save(path)

    loaded = CorrectionMemory.load(path)
    assert len(loaded.all()) == 1
    assert loaded.all()[0].correction_id == "c1"


def test_load_missing_file_returns_empty_memory(tmp_path):
    loaded = CorrectionMemory.load(tmp_path / "does_not_exist.json")
    assert loaded.all() == []


# --- from_approval.py -------------------------------------------------

def _approve_outcome():
    req = ApprovalRequest(resume_id="res_x", action="classify_candidate", risk_score=0.1,
                           recommendation="automate_with_monitoring", reason="x", gate_required=True)
    return apply_decision(req, "approve")


def test_approve_decision_never_becomes_a_correction_record():
    """A correction store that recorded approvals would misrepresent
    how often the AI was actually overridden — Section 24 is about
    corrections, not agreements."""
    record = correction_from_outcome(_approve_outcome())
    assert record is None


@pytest.mark.parametrize("decision,needs_payload", [("edit", True), ("reject", False), ("escalate", False)])
def test_non_approve_decisions_become_correction_records(decision, needs_payload):
    req = ApprovalRequest(resume_id="res_y", action="send_interview_invitation", risk_score=1.0,
                           recommendation="approval_required", reason="hard override", gate_required=True)
    payload = {"note": "edited"} if needs_payload else None
    outcome = apply_decision(req, decision, edited_payload=payload)

    record = correction_from_outcome(outcome)
    assert record is not None
    assert record.human_correction == decision
    assert record.workflow_context == {"workflow": "resume_screening", "resume_id": "res_y", "action": "send_interview_invitation"}
    assert record.original_ai_decision["recommendation"] == "approval_required"


# --- build_correction_memory.py: simulate_decision ----------------------

def test_simulate_decision_never_auto_approves_approval_required():
    req = ApprovalRequest(resume_id="res_x", action="send_interview_invitation", risk_score=1.0,
                           recommendation="approval_required", reason="x", gate_required=True)
    decision, _ = simulate_decision(req)
    assert decision == "escalate"


def test_simulate_decision_rejects_human_review_failures():
    req = ApprovalRequest(resume_id="res_x", action="extract_resume", risk_score=1.0,
                           recommendation="human_review", reason="x", gate_required=True)
    decision, payload = simulate_decision(req)
    assert decision == "reject"
    assert payload is None


def test_simulate_decision_edits_monitoring_cases_with_a_payload():
    req = ApprovalRequest(resume_id="res_x", action="classify_candidate", risk_score=0.3,
                           recommendation="automate_with_monitoring", reason="x", gate_required=True)
    decision, payload = simulate_decision(req)
    assert decision == "edit"
    assert payload is not None


def test_simulate_decision_raises_on_automate_recommendation():
    """automate cases should never reach the gate/simulator at all
    (build_approval_queue filters them out) — if one ever did, this
    must fail loudly rather than silently simulate a decision for it."""
    req = ApprovalRequest(resume_id="res_x", action="fetch_resume", risk_score=0.1,
                           recommendation="automate", reason="x", gate_required=False)
    with pytest.raises(ValueError):
        simulate_decision(req)


# --- real data (S7: generated, not hand-typed) ---------------------------

def test_real_correction_memory_matches_day11_queue_size_and_is_labeled_simulated():
    queue = json.loads((RESULTS_DIR / "day11_approval_queue.json").read_text())
    memory_data = json.loads((RESULTS_DIR / "day12_correction_memory.json").read_text())
    assert len(memory_data) == len(queue) == 16
    assert all(r["source"] == "simulated_demo" for r in memory_data)
    assert all(r["human_correction"] in {"edit", "reject", "escalate"} for r in memory_data)


def test_real_correction_memory_action_breakdown():
    memory_data = json.loads((RESULTS_DIR / "day12_correction_memory.json").read_text())
    from collections import Counter

    counts = Counter(r["workflow_context"]["action"] for r in memory_data)
    assert counts == {"send_interview_invitation": 10, "classify_candidate": 4, "extract_resume": 2}


# --- workflow_version.py / version_diff.py (Section 25) ------------------

def test_build_versions_returns_four_versions_in_order():
    versions = build_versions()
    assert [v.version for v in versions] == [1, 2, 3, 4]
    assert [v.reached for v in versions] == [True, True, True, False]


def test_v4_metrics_are_honestly_empty_not_fabricated():
    versions = build_versions()
    v4 = versions[-1]
    assert v4.reached is False
    assert v4.metrics == {}


def test_v3_automation_coverage_matches_day10_real_numbers():
    risk_scores = json.loads((RESULTS_DIR / "day10_risk_scores.json").read_text())
    expected_automate = sum(1 for s in risk_scores if s["recommendation"] == "automate")
    expected_pct = round(100 * expected_automate / len(risk_scores), 1)

    versions = build_versions()
    v3 = next(v for v in versions if v.version == 3)
    assert v3.metrics["automation_coverage_pct"] == expected_pct == 78.4


def test_diff_reports_added_removed_and_changed_metrics():
    v_from = WorkflowVersion(version=1, label="A", description="", built_in_day=1, reached=True,
                              metrics={"shared": 1, "only_in_from": "x"})
    v_to = WorkflowVersion(version=2, label="B", description="", built_in_day=2, reached=True,
                            metrics={"shared": 2, "only_in_to": "y"})
    d = diff(v_from, v_to)
    assert d["changed_metrics"]["shared"] == {"before": 1, "after": 2}
    assert d["changed_metrics"]["only_in_from"] == {"before": "x", "after": "<not tracked>"}
    assert d["changed_metrics"]["only_in_to"] == {"before": "<not tracked>", "after": "y"}


def test_diff_detects_reached_state_change():
    v3 = WorkflowVersion(version=3, label="A", description="", built_in_day=11, reached=True, metrics={})
    v4 = WorkflowVersion(version=4, label="B", description="", built_in_day=13, reached=False, metrics={})
    d = diff(v3, v4)
    assert d["reached_change"] == {"before": True, "after": False}


def test_diff_all_consecutive_produces_three_diffs_for_four_versions():
    versions = build_versions()
    diffs = diff_all_consecutive(versions)
    assert len(diffs) == 3
    assert [(d["from_version"], d["to_version"]) for d in diffs] == [(1, 2), (2, 3), (3, 4)]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
