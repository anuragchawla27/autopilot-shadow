"""
Day 9 validation: proves the comparison engine correctly normalizes
different event shapes between human/AI sources, handles the documented
logging-granularity asymmetry, and - critically - correctly DETECTS
disagreement when it exists, using hand-constructed synthetic mismatches
(since the real dataset shows near-total agreement by construction, see
docs/11 for why that's an honest, expected finding, not something to
hide).

Run: python -m pytest tests/test_comparison_day9.py -v
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from autopilot_shadow.comparison.agreement import score_dataset, score_resume
from autopilot_shadow.comparison.engine import (
    ai_resume_id_from_demo_id,
    compare_all,
    compare_resume,
    human_resume_id_from_demo_id,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def human_events():
    return json.loads((DATA_DIR / "demonstrations.json").read_text())


@pytest.fixture
def ai_events():
    return json.loads((DATA_DIR / "shadow_run.json").read_text())


# --- demo_id parsing -------------------------------------------------

def test_human_resume_id_parsing_excludes_dup_and_fault_demos():
    assert human_resume_id_from_demo_id("demo_0001_res_0001") == "res_0001"
    assert human_resume_id_from_demo_id("demo_dup_0001_res_0011") is None
    assert human_resume_id_from_demo_id("demo_fault_tool_failure") is None


def test_ai_resume_id_parsing():
    assert ai_resume_id_from_demo_id("shadow_res_0001") == "res_0001"
    assert ai_resume_id_from_demo_id("demo_0001_res_0001") is None


# --- real-data behavior ------------------------------------------------

def test_compares_all_12_resumes(human_events, ai_events):
    comparisons = compare_all(human_events, ai_events)
    assert len(comparisons) == 12
    assert {c["resume_id"] for c in comparisons} == {f"res_{i:04d}" for i in range(1, 13)}


def test_dup_and_fault_demos_excluded_from_comparison(human_events, ai_events):
    """Guards against accidentally comparing against the artificial Day 4
    exception-testing demos instead of the plain per-resume ones."""
    comparisons = compare_all(human_events, ai_events)
    res_0011_comparisons = [c for c in comparisons if c["resume_id"] == "res_0011"]
    assert len(res_0011_comparisons) == 1  # not 2 (would be 2 if demo_dup_0001_res_0011 also matched)


def test_real_dataset_shows_full_agreement_by_construction(human_events, ai_events):
    """HONEST, EXPECTED FINDING (see docs/11): the human demo policy
    (Day 4) and the AI's shadow logic (Day 7/8) were both written by us
    from the SAME underlying rules, so they agree on every dimension for
    this synthetic dataset. This is a real property of the data, not a
    sign the engine always reports 'match' - see the synthetic-mismatch
    tests below for proof the engine correctly detects real
    disagreement when it exists."""
    comparisons = compare_all(human_events, ai_events)
    scores = score_dataset(comparisons)
    for dim, d in scores["dimensions"].items():
        assert d["rate"] == 1.0, f"{dim} unexpectedly below 1.0 on the real dataset"
    assert scores["outcome_disagreements"] == []


def test_send_interview_invitation_asymmetry_handled_as_match_not_mismatch(human_events, ai_events):
    """res_0002 (rejected): human demo never logs this step at all;
    AI shadow always logs it as a proposed no-op. Must be treated as
    agreement (both represent 'no email'), not penalized as a mismatch."""
    comparison = compare_resume(
        "res_0002",
        [e for e in human_events if e["demo_id"] == "demo_0002_res_0002"],
        [e for e in ai_events if e["demo_id"] == "shadow_res_0002"],
    )
    send_step = next(s for s in comparison["steps"] if s["action"] == "send_interview_invitation")
    assert send_step["human_present"] is False
    assert send_step["ai_present"] is True
    assert send_step["match"] is True  # outcome-equivalent, not penalized
    assert comparison["outcome_agreement"] is True


def test_identical_exception_failures_compare_exception_type_not_empty_output(human_events, ai_events):
    """res_0009: both sides fail at extract_resume with empty output.
    Comparing exception_type (not the trivially-empty output dict) is
    what makes this a MEANINGFUL match rather than a coincidental one."""
    comparison = compare_resume(
        "res_0009",
        [e for e in human_events if e["demo_id"] == "demo_0009_res_0009"],
        [e for e in ai_events if e["demo_id"] == "shadow_res_0009"],
    )
    extract_step = next(s for s in comparison["steps"] if s["action"] == "extract_resume")
    assert extract_step["human_value"]["failed"] is True
    assert extract_step["human_value"]["exception_type"] == "missing_document"
    assert extract_step["ai_value"]["exception_type"] == "missing_document"
    assert extract_step["match"] is True


# --- synthetic mismatch tests: proving the mechanism works -------------

def test_engine_detects_a_real_decision_mismatch():
    """Hand-constructed: human classified 'shortlist', AI proposed
    'reject' for the identical case - the engine MUST report this as a
    mismatch and it must pull decision_agreement below 1.0."""
    human = [
        {
            "demo_id": "demo_x_res_x", "action": "classify_candidate", "step_index": 0, "result": "success",
            "application": "hr_policy", "output": {}, "decision": {"outcome": "shortlist"},
        }
    ]
    ai = [
        {
            "demo_id": "shadow_res_x", "action": "classify_candidate", "step_index": 0, "result": "success",
            "application": "hr_policy", "output": {}, "decision": {"outcome": "reject"}, "confidence": 0.5,
        }
    ]
    comparison = compare_resume("res_x", human, ai)
    classify_step = comparison["steps"][0]
    assert classify_step["match"] is False
    assert comparison["outcome_agreement"] is False

    score = score_resume(comparison)
    assert score["decision_agreement"]["rate"] == 0.0


def test_engine_detects_a_tool_mismatch():
    """Hand-constructed: both sides took 'fetch_resume' but used a
    different application - must be flagged as a tool disagreement,
    independent of whether the data itself matched."""
    human = [
        {
            "demo_id": "demo_x_res_x", "action": "fetch_resume", "step_index": 0, "result": "success",
            "application": "resume_db", "output": {"resume_id": "res_x"}, "decision": None,
        }
    ]
    ai = [
        {
            "demo_id": "shadow_res_x", "action": "fetch_resume", "step_index": 0, "result": "success",
            "application": "legacy_resume_archive", "output": {"resume_id": "res_x"}, "decision": None, "confidence": 0.9,
        }
    ]
    comparison = compare_resume("res_x", human, ai)
    fetch_step = comparison["steps"][0]
    assert fetch_step["tool_agreement"] is False
    assert fetch_step["match"] is True  # data itself still agrees

    score = score_resume(comparison)
    assert score["tool_agreement"]["rate"] == 0.0
    assert score["action_agreement"]["rate"] == 1.0  # independent dimensions, not conflated


def test_engine_detects_a_data_extraction_mismatch():
    """Hand-constructed: AI extracted a different experience_years value
    than the human - a genuine data disagreement, not a decision one."""
    human = [
        {
            "demo_id": "demo_x_res_x", "action": "extract_resume", "step_index": 0, "result": "success",
            "application": "document_parser", "output": {"experience_years": 3.0, "skills": ["sql"], "candidate_name": "X"},
            "decision": None,
        }
    ]
    ai = [
        {
            "demo_id": "shadow_res_x", "action": "extract_resume", "step_index": 0, "result": "success",
            "application": "document_parser", "output": {"experience_years": 5.0, "skills": ["sql"], "candidate_name": "X"},
            "decision": None, "confidence": 0.99,
        }
    ]
    comparison = compare_resume("res_x", human, ai)
    extract_step = comparison["steps"][0]
    assert extract_step["match"] is False

    score = score_resume(comparison)
    assert score["data_agreement"]["rate"] == 0.0


def test_dataset_level_rollup_averages_across_mixed_agreement_and_disagreement():
    """Two synthetic resumes: one full agreement, one full decision
    mismatch - dataset-level decision_agreement rate must be exactly 0.5,
    and the mismatched resume must appear in outcome_disagreements."""
    human = [
        {"demo_id": "demo_a_res_a", "action": "classify_candidate", "step_index": 0, "result": "success",
         "application": "hr_policy", "output": {}, "decision": {"outcome": "shortlist"}},
        {"demo_id": "demo_b_res_b", "action": "classify_candidate", "step_index": 0, "result": "success",
         "application": "hr_policy", "output": {}, "decision": {"outcome": "shortlist"}},
    ]
    ai = [
        {"demo_id": "shadow_res_a", "action": "classify_candidate", "step_index": 0, "result": "success",
         "application": "hr_policy", "output": {}, "decision": {"outcome": "shortlist"}, "confidence": 0.9},
        {"demo_id": "shadow_res_b", "action": "classify_candidate", "step_index": 0, "result": "success",
         "application": "hr_policy", "output": {}, "decision": {"outcome": "reject"}, "confidence": 0.3},
    ]
    comparisons = compare_all(human, ai)
    scores = score_dataset(comparisons)
    assert scores["dimensions"]["decision_agreement"]["rate"] == 0.5
    assert len(scores["outcome_disagreements"]) == 1
    assert scores["outcome_disagreements"][0]["resume_id"] == "res_b"


def test_dimensions_are_never_collapsed_into_one_number(human_events, ai_events):
    """Structural check on Section 14's explicit requirement: the
    dataset-level result must expose 5 separate dimension dicts, never a
    single combined score field."""
    comparisons = compare_all(human_events, ai_events)
    scores = score_dataset(comparisons)
    assert set(scores["dimensions"].keys()) == {
        "action_agreement", "data_agreement", "decision_agreement", "tool_agreement", "outcome_agreement",
    }
    assert "overall_score" not in scores
    assert "combined_score" not in scores


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
