"""
Day 10 validation: the risk model's static factors, the formula's exact
arithmetic, the two hard overrides (Section 22 safety, failed steps),
and that it actually resolves D-033's deferred finding (two cases that
Day 7 classified identically now get different scores once per-case
confidence is in the formula).

Run: python -m pytest tests/test_risk_model_day10.py -v
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from autopilot_shadow.risk.historical_agreement import per_action_agreement
from autopilot_shadow.risk.risk_factors import ACTION_RISK_FACTORS, impact_score
from autopilot_shadow.risk.risk_model import score_case

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"


# --- risk_factors.py ----------------------------------------------------

def test_every_workflow_action_has_risk_factors():
    """Guards against a future day adding a new action without also
    defining its risk factors (score_case raises KeyError otherwise)."""
    expected_actions = {
        "fetch_resume", "extract_resume", "check_experience", "compare_skills",
        "classify_candidate", "update_candidate_record", "send_interview_invitation",
    }
    assert expected_actions <= set(ACTION_RISK_FACTORS)


def test_impact_score_is_average_of_four_components():
    factors = ACTION_RISK_FACTORS["fetch_resume"]
    # reversible=True->0, external=False->0, financial=low->0, privacy=high->1
    assert impact_score(factors) == pytest.approx(0.25)

    factors = ACTION_RISK_FACTORS["send_interview_invitation"]
    # irreversible->1, external->1, financial=medium->0.5, privacy=high->1
    assert impact_score(factors) == pytest.approx(0.875)

    factors = ACTION_RISK_FACTORS["check_experience"]
    # reversible->0, internal->0, financial=low->0, privacy=low->0
    assert impact_score(factors) == pytest.approx(0.0)


def test_send_interview_invitation_has_the_highest_impact_score():
    """The brief's own table singles this action out as the highest-risk
    step in the workflow (Section 22's hard safety example) — the
    computed impact score must reflect that ordering, not just assert it."""
    send_impact = impact_score(ACTION_RISK_FACTORS["send_interview_invitation"])
    other_impacts = [
        impact_score(f) for a, f in ACTION_RISK_FACTORS.items() if a != "send_interview_invitation"
    ]
    assert send_impact > max(other_impacts)


# --- historical_agreement.py --------------------------------------------

def test_per_action_agreement_aggregates_across_resumes():
    comparisons = [
        {"steps": [
            {"action": "fetch_resume", "match": True},
            {"action": "classify_candidate", "match": True},
        ]},
        {"steps": [
            {"action": "fetch_resume", "match": True},
            {"action": "classify_candidate", "match": False},
        ]},
    ]
    result = per_action_agreement(comparisons)
    assert result["fetch_resume"] == {"matched": 2, "evaluable": 2, "rate": 1.0}
    assert result["classify_candidate"] == {"matched": 1, "evaluable": 2, "rate": 0.5}


def test_per_action_agreement_skips_non_evaluable_steps():
    """A step present on only one side (match=None would not occur in
    Day 9's real output, but a step explicitly excluded from scoring,
    e.g. via a None match, must not be silently counted as agreement."""
    comparisons = [{"steps": [{"action": "weird_step", "match": None}]}]
    result = per_action_agreement(comparisons)
    assert "weird_step" not in result


# --- risk_model.py: hard overrides --------------------------------------

def test_irreversible_external_action_always_forced_to_approval_required():
    """Section 22's hard safety rule: even a near-perfect confidence and
    perfect historical agreement cannot talk this action down."""
    score = score_case(
        action="send_interview_invitation", resume_id="res_x",
        confidence=0.999, result="success", historical_agreement_rate=1.0,
    )
    assert score.recommendation == "approval_required"
    assert score.risk_score == 1.0


def test_failed_step_forced_to_human_review_regardless_of_nominal_confidence():
    """The bug this override fixes: Day 8 logs confidence=0.99 (the
    fixed 'deterministic step' value) even on a step that FAILED. That
    number describes how much judgment the computation involves, not
    whether it actually worked, so it must never be used to score a
    failure as a confident automate case."""
    score = score_case(
        action="extract_resume", resume_id="res_x",
        confidence=0.99, result="failure", historical_agreement_rate=1.0,
    )
    assert score.recommendation == "human_review"
    assert score.risk_score == 1.0


def test_unknown_action_raises_instead_of_silently_scoring():
    with pytest.raises(KeyError):
        score_case(
            action="not_a_real_action", resume_id="res_x",
            confidence=0.9, result="success", historical_agreement_rate=1.0,
        )


def test_missing_historical_agreement_falls_back_to_uncertainty():
    """If an action has no Day 9 comparison data at all (e.g. a brand
    new workflow step with no human trace yet), the model must not
    silently treat that as 'agreement unknown = 0 disagreement' — it
    falls back to using this case's own uncertainty as a conservative
    substitute, and says so in the reason text."""
    score = score_case(
        action="check_experience", resume_id="res_x",
        confidence=0.8, result="success", historical_agreement_rate=None,
    )
    assert score.disagreement == score.uncertainty == 0.2
    assert "no historical agreement data" in score.reason


# --- risk_model.py: exact formula arithmetic -----------------------------

def test_formula_arithmetic_is_exact_for_a_hand_computed_case():
    """update_candidate_record: impact=0.125 (reversible, internal,
    financial=low->0, privacy=medium->0.5, avg=0.125). confidence=0.9 ->
    uncertainty=0.1. historical_agreement=0.8 -> disagreement=0.2.
    risk = 0.5*0.125 + 0.3*0.1 + 0.2*0.2 = 0.0625 + 0.03 + 0.04 = 0.1325"""
    score = score_case(
        action="update_candidate_record", resume_id="res_x",
        confidence=0.9, result="success", historical_agreement_rate=0.8,
    )
    assert score.impact_score == pytest.approx(0.125)
    assert score.uncertainty == pytest.approx(0.1)
    assert score.disagreement == pytest.approx(0.2)
    assert score.risk_score == pytest.approx(0.1325)


# --- resolves D-033: same step, different cases, different scores -------

def test_resolves_d033_same_step_different_confidence_gives_different_risk():
    """D-033's honest finding (Day 7): res_0001 (clean explicit-rule
    match) and res_0004 (ambiguous unknown-rule case) halt at the SAME
    step under Day 7's per-STEP classification. Day 10's per-CASE risk
    model is exactly what was deferred to resolve this — the two cases
    must now get genuinely different scores and different
    recommendations, because their confidence differs (0.95 vs 0.40)."""
    clean_case = score_case(
        action="classify_candidate", resume_id="res_0001",
        confidence=0.95, result="success", historical_agreement_rate=1.0,
    )
    ambiguous_case = score_case(
        action="classify_candidate", resume_id="res_0004",
        confidence=0.40, result="success", historical_agreement_rate=1.0,
    )
    assert clean_case.risk_score < ambiguous_case.risk_score
    assert clean_case.recommendation == "automate"
    assert ambiguous_case.recommendation == "automate_with_monitoring"


# --- real data (S7: generated, not hand-typed) ---------------------------

def test_real_shadow_run_scores_every_event_without_crashing():
    shadow_events = json.loads((DATA_DIR / "shadow_run.json").read_text())
    comparisons = json.loads((RESULTS_DIR / "day09_comparisons.json").read_text())
    agreement = per_action_agreement(comparisons)

    scores = []
    for evt in shadow_events:
        scores.append(
            score_case(
                action=evt["action"],
                resume_id=evt["demo_id"].replace("shadow_", ""),
                confidence=evt.get("confidence"),
                result=evt["result"],
                historical_agreement_rate=agreement.get(evt["action"], {}).get("rate"),
            )
        )
    assert len(scores) == len(shadow_events) == 74


def test_real_data_send_interview_invitation_always_approval_required():
    shadow_events = json.loads((DATA_DIR / "shadow_run.json").read_text())
    comparisons = json.loads((RESULTS_DIR / "day09_comparisons.json").read_text())
    agreement = per_action_agreement(comparisons)

    send_events = [e for e in shadow_events if e["action"] == "send_interview_invitation"]
    # Day 8's ShadowExecutor never halts (D-034/D-035) — it logs this step, even as an
    # explicit no-op, for every resume that reaches it. Only res_0009/res_0010 (failed at
    # extract_resume) never reach it at all. 12 - 2 = 10, regardless of classification.
    assert len(send_events) == 10
    for evt in send_events:
        score = score_case(
            action=evt["action"], resume_id=evt["demo_id"],
            confidence=evt.get("confidence"), result=evt["result"],
            historical_agreement_rate=agreement.get(evt["action"], {}).get("rate"),
        )
        assert score.recommendation == "approval_required"


def test_real_data_failed_extractions_are_human_review():
    shadow_events = json.loads((DATA_DIR / "shadow_run.json").read_text())
    comparisons = json.loads((RESULTS_DIR / "day09_comparisons.json").read_text())
    agreement = per_action_agreement(comparisons)

    failed = [e for e in shadow_events if e["result"] == "failure"]
    assert len(failed) == 2  # res_0009, res_0010
    for evt in failed:
        score = score_case(
            action=evt["action"], resume_id=evt["demo_id"],
            confidence=evt.get("confidence"), result=evt["result"],
            historical_agreement_rate=agreement.get(evt["action"], {}).get("rate"),
        )
        assert score.recommendation == "human_review"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
