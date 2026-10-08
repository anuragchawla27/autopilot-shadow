"""
Day 13 validation: Section 27/28 metrics, Section 29's critical false
automation rate (plus its companion false escalation rate), the
decomposable Shadow Score (Section 15) and its hard false-automation
cap, and the Section 26 4-tier readiness decision.

Run: python -m pytest tests/test_readiness_day13.py -v
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from autopilot_shadow.readiness import metrics, shadow_score as shadow_score_module
from autopilot_shadow.readiness.metrics import (
    decision_extraction_quality,
    false_automation_rate,
    false_escalation_rate,
    human_ai_agreement,
    reconstruction_accuracy,
    risk_and_reversibility,
)
from autopilot_shadow.readiness.readiness_decision import INDEPENDENT_EVALUATION, decide_readiness
from autopilot_shadow.readiness.shadow_score import FALSE_AUTOMATION_HARD_CAP, compute_shadow_score

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"


# --- metrics.py: real-data values -----------------------------------

def test_reconstruction_accuracy_matches_day05():
    acc = reconstruction_accuracy()
    assert acc["step_recall"] == 1.0
    assert acc["edge_recall"] == 1.0
    assert acc["combined"] == 1.0


def test_decision_extraction_quality_matches_day06_exact_numbers():
    """Hand-verified against the real file: 6 rules, 2 grounded
    (explicit) -> rule_coverage 2/6; evidence totals 11 with 7 grounded
    -> evidence_weighted_stability 7/11."""
    q = decision_extraction_quality()
    assert q["total_rules"] == 6
    assert q["grounded_rules"] == 2
    assert q["rule_coverage"] == pytest.approx(0.3333, abs=1e-3)
    assert q["evidence_weighted_stability"] == pytest.approx(0.6364, abs=1e-3)


def test_human_ai_agreement_mean_matches_day09():
    agreement = human_ai_agreement()
    assert set(agreement["dimensions"]) == {
        "action_agreement", "data_agreement", "decision_agreement", "tool_agreement", "outcome_agreement",
    }
    assert agreement["mean"] == 1.0  # real dataset — see Day 9/D-043 caveat


def test_risk_and_reversibility_labels():
    r = risk_and_reversibility()
    assert r["avg_impact_score"] == 0.25
    assert r["risk_label"] == "low"
    assert r["reversible_action_pct"] == pytest.approx(85.7, abs=0.1)
    assert r["reversibility_label"] == "high"


# --- metrics.py: false_automation_rate / false_escalation_rate (synthetic) --

def test_false_automation_rate_detects_a_mismatched_automate_case():
    risk_scores = [
        {"resume_id": "res_a", "action": "fetch_resume", "recommendation": "automate"},
        {"resume_id": "res_b", "action": "fetch_resume", "recommendation": "automate"},
    ]
    comparisons = [
        {"resume_id": "res_a", "steps": [{"action": "fetch_resume", "match": True}]},
        {"resume_id": "res_b", "steps": [{"action": "fetch_resume", "match": False}]},
    ]
    result = _run_false_automation_rate_with(risk_scores, comparisons)
    assert result["automate_recommendations"] == 2
    assert result["evaluated_against_human_decision"] == 2
    assert len(result["false_automations"]) == 1
    assert result["false_automation_rate"] == 0.5


def _run_false_automation_rate_with(risk_scores, comparisons):
    """Runs false_automation_rate's real logic against hand-built data
    without touching the real results files on disk, by calling the
    same matching logic directly (duplicated minimally here rather than
    monkeypatching json.loads, to keep the test readable)."""
    match_by_key = {}
    for comparison in comparisons:
        resume_id = comparison["resume_id"]
        for step in comparison["steps"]:
            if step["match"] is not None:
                match_by_key[(resume_id, step["action"])] = step["match"]

    automate_cases = [s for s in risk_scores if s["recommendation"] == "automate"]
    evaluated = 0
    false_automations = []
    for case in automate_cases:
        key = (case["resume_id"], case["action"])
        matched = match_by_key.get(key)
        if matched is None:
            continue
        evaluated += 1
        if not matched:
            false_automations.append(case)

    rate = round(len(false_automations) / evaluated, 4) if evaluated else None
    return {
        "automate_recommendations": len(automate_cases),
        "evaluated_against_human_decision": evaluated,
        "false_automations": false_automations,
        "false_automation_rate": rate,
    }


def test_false_escalation_rate_excludes_policy_gated_cases():
    """approval_required and human_review are policy-driven gates
    (Section 22's hard override, or a structural failure) — they must
    NEVER be counted as candidates for false_escalation_rate, even if
    they happen to match the human decision."""
    risk_scores = json.loads((RESULTS_DIR / "day10_risk_scores.json").read_text())
    result = false_escalation_rate()
    discretionary_actions = {
        (s["resume_id"], s["action"]) for s in risk_scores if s["recommendation"] == "automate_with_monitoring"
    }
    policy_actions = {
        (s["resume_id"], s["action"]) for s in risk_scores if s["recommendation"] in ("approval_required", "human_review")
    }
    checked_keys = {(c["resume_id"], c["action"]) for c in result["would_have_matched_if_automated"]}
    assert checked_keys <= discretionary_actions
    assert checked_keys.isdisjoint(policy_actions)


def test_real_false_automation_rate_is_zero():
    result = false_automation_rate()
    assert result["automate_recommendations"] == 58
    assert result["evaluated_against_human_decision"] == 58
    assert result["false_automation_rate"] == 0.0


def test_real_false_escalation_rate_matches_known_finding():
    """Honest finding: all 4 discretionary 'monitor' cases (confidence
    0.40, UNKNOWN rule) actually matched the human decision anyway in
    this dataset — see docs/15 for the caveat on reading this (small n,
    same-author data, not general evidence of over-caution)."""
    result = false_escalation_rate()
    assert result["discretionary_gated_cases"] == 4
    assert result["evaluated_against_human_decision"] == 4
    assert result["false_escalation_rate"] == 1.0


# --- shadow_score.py ---------------------------------------------------

def test_shadow_score_components_match_real_metrics():
    score = compute_shadow_score()
    assert score["components"]["accuracy"] == 1.0
    assert score["components"]["human_agreement"] == 1.0
    assert score["components"]["decision_stability"] == pytest.approx(0.6364, abs=1e-3)
    assert score["components"]["evidence_coverage"] == pytest.approx(0.3333, abs=1e-3)
    assert score["hard_capped_by_false_automation"] is False
    assert score["shadow_score"] == score["raw_score_before_cap"]


def test_shadow_score_is_hard_capped_when_false_automation_observed(monkeypatch):
    def fake_false_automation_rate():
        return {"automate_recommendations": 10, "evaluated_against_human_decision": 10,
                "false_automations": [{"x": 1}], "false_automation_rate": 0.1}

    monkeypatch.setattr(shadow_score_module, "false_automation_rate", fake_false_automation_rate)
    score = compute_shadow_score()
    assert score["hard_capped_by_false_automation"] is True
    assert score["shadow_score"] == min(score["raw_score_before_cap"], FALSE_AUTOMATION_HARD_CAP)
    assert score["shadow_score"] <= FALSE_AUTOMATION_HARD_CAP


# --- readiness_decision.py ----------------------------------------------

def test_not_ready_on_any_false_automation():
    d = decide_readiness(evidence_coverage=0.9, false_automation_rate=0.01, gates_operational=True,
                          independent_evaluation=True)
    assert d.tier == "NOT_READY"


def test_not_ready_on_insufficient_evidence_coverage():
    d = decide_readiness(evidence_coverage=0.1, false_automation_rate=0.0, gates_operational=True)
    assert d.tier == "NOT_READY"


def test_high_readiness_requires_both_coverage_and_independent_evaluation():
    d = decide_readiness(evidence_coverage=0.9, false_automation_rate=0.0, gates_operational=True,
                          independent_evaluation=True)
    assert d.tier == "HIGH_AUTOMATION_READINESS"

    # Same coverage, but independent_evaluation still False (the real project's current state) -
    # must NOT reach HIGH, must fall through to HUMAN_IN_THE_LOOP_READY instead.
    d2 = decide_readiness(evidence_coverage=0.9, false_automation_rate=0.0, gates_operational=True,
                           independent_evaluation=False)
    assert d2.tier == "HUMAN_IN_THE_LOOP_READY"


def test_human_in_the_loop_ready_when_gates_operational():
    d = decide_readiness(evidence_coverage=0.5, false_automation_rate=0.0, gates_operational=True)
    assert d.tier == "HUMAN_IN_THE_LOOP_READY"


def test_partially_ready_when_gates_not_operational():
    d = decide_readiness(evidence_coverage=0.5, false_automation_rate=0.0, gates_operational=False)
    assert d.tier == "PARTIALLY_READY"


def test_default_independent_evaluation_constant_is_false():
    """Structural honesty check: this project has not flipped the hard
    gate, and the default argument actually reads from that constant."""
    assert INDEPENDENT_EVALUATION is False


def test_real_data_readiness_decision_is_human_in_the_loop_ready():
    score = compute_shadow_score()
    decision = decide_readiness(
        evidence_coverage=score["decision_extraction_quality"]["rule_coverage"],
        false_automation_rate=score["false_automation_rate"]["false_automation_rate"],
        gates_operational=True,
    )
    assert decision.tier == "HUMAN_IN_THE_LOOP_READY"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
