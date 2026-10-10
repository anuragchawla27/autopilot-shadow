"""
Case 3 — "AI has high confidence but is wrong" (Day 14, Section 23 /
Section 21's "high confidence does not mean high correctness").

Two separate things happen here, deliberately kept apart:

1. REAL CALIBRATION CHECK (`calibration_report`): for every real
   classify_candidate case in the 12-resume dataset, compare the
   shadow engine's confidence (Day 8) against whether its decision
   matches `data/ground_truth.json` — NOT against the human demo
   policy. This is a genuine change from Day 9's agreement metric: the
   human policy and the AI's classifier were written by the same
   author from the same rules (D-043), so AI-vs-human agreement can't
   tell us anything about calibration. Ground truth is a separate,
   independently-written label set (Day 1/5's hand-built test
   labels), so comparing confidence against ground-truth correctness
   is the more honest signal available in this project, though it is
   still only 12 cases and still the same author's own judgment calls
   (documented plainly in the output, not glossed over).

2. SAFETY-UNDER-MISCALIBRATION CHECK (`high_confidence_wrong_is_still_safe`):
   a synthetic case (same pattern as D-043/D-054) where the AI is
   deliberately given a high confidence (0.95) for a WRONG decision on
   an irreversible+external action, proving Section 22's hard risk
   override (risk/risk_model.py) still forces `approval_required`
   regardless of how confident the (wrong) AI claims to be. This is
   the actual point of Case 3 for THIS system: not "can we make the
   classifier always right" (no system can), but "does a confidently
   wrong answer ever get to act without a human" (it must not, and
   this proves it doesn't).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from autopilot_shadow.risk.risk_factors import ACTION_RISK_FACTORS
from autopilot_shadow.risk.risk_model import score_case

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
RESULTS_DIR = Path(__file__).resolve().parents[3] / "results"

CONFIDENCE_BINS = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.01)]


@dataclass(frozen=True)
class CalibrationBin:
    low: float
    high: float
    n: int
    mean_confidence: Optional[float]
    accuracy: Optional[float]
    gap: Optional[float]  # |mean_confidence - accuracy|


@dataclass(frozen=True)
class CalibrationReport:
    n_cases: int
    bins: list[CalibrationBin]
    expected_calibration_error: float
    worst_case: Optional[dict]  # the single case with the largest confidence/correctness gap, if any
    caveat: str


def _load(path: Path) -> dict | list:
    return json.loads(path.read_text())


def calibration_report(
    comparisons_path: Path = RESULTS_DIR / "day09_comparisons.json",
    ground_truth_path: Path = DATA_DIR / "ground_truth.json",
) -> CalibrationReport:
    comparisons = _load(comparisons_path)
    ground_truth = _load(ground_truth_path)["labels"]

    cases = []
    for demo in comparisons:
        resume_id = demo["resume_id"]
        label = ground_truth.get(resume_id)
        if label is None:
            continue
        step = next((s for s in demo["steps"] if s["action"] == "classify_candidate"), None)
        if step is None or not step.get("ai_present"):
            continue
        ai_outcome = step["ai_value"].get("outcome")
        confidence = step["ai_confidence"]
        correct = ai_outcome == label["expected_decision"]
        cases.append(
            {
                "resume_id": resume_id,
                "ai_outcome": ai_outcome,
                "expected_decision": label["expected_decision"],
                "confidence": confidence,
                "correct": correct,
            }
        )

    bins = []
    ece_numerator = 0.0
    worst_case = None
    worst_gap = -1.0
    for low, high in CONFIDENCE_BINS:
        in_bin = [c for c in cases if low <= c["confidence"] < high]
        if not in_bin:
            bins.append(CalibrationBin(low, high, 0, None, None, None))
            continue
        mean_conf = sum(c["confidence"] for c in in_bin) / len(in_bin)
        accuracy = sum(1 for c in in_bin if c["correct"]) / len(in_bin)
        gap = abs(mean_conf - accuracy)
        bins.append(CalibrationBin(low, high, len(in_bin), round(mean_conf, 4), round(accuracy, 4), round(gap, 4)))
        ece_numerator += len(in_bin) * gap

        for c in in_bin:
            case_gap = c["confidence"] if not c["correct"] else 0.0  # a wrong case's own confidence is its own "surprise"
            if case_gap > worst_gap:
                worst_gap = case_gap
                worst_case = c

    ece = round(ece_numerator / len(cases), 4) if cases else 0.0

    return CalibrationReport(
        n_cases=len(cases),
        bins=bins,
        expected_calibration_error=ece,
        worst_case=worst_case,
        caveat=(
            "Computed against data/ground_truth.json (independently hand-labelled test set), "
            "not against the human demo policy, because the policy and the AI classifier share "
            "an author (D-043) and so cannot evaluate calibration on their own. Still only 12 "
            "cases — not enough to draw a general calibration conclusion, reported honestly "
            "rather than treated as a tuned result (S7)."
        ),
    )


@dataclass(frozen=True)
class SafetyUnderMiscalibrationResult:
    scenario: str
    forced_confidence: float
    forced_decision_was_wrong: bool
    recommendation: str
    gate_required: bool
    passed: bool
    explanation: str


def high_confidence_wrong_is_still_safe() -> SafetyUnderMiscalibrationResult:
    """Synthetic case: the AI is given 0.95 confidence for a decision we
    know (by construction) is wrong, on `send_interview_invitation` —
    irreversible + external. Proves the hard override in
    `risk/risk_model.py` does not consult confidence at all for this
    class of action, so a confidently wrong AI still cannot act alone.
    """
    action = "send_interview_invitation"
    factors = ACTION_RISK_FACTORS[action]
    assert not factors.reversible and factors.external_facing, (
        "This scenario only proves what it claims to prove if the action is irreversible+external; "
        "if risk_factors.py ever changes this action's profile, this assertion will fail loudly "
        "rather than silently pass a case that no longer tests the override."
    )

    risk = score_case(
        action=action,
        resume_id="synthetic_case3",
        confidence=0.95,  # deliberately high
        result="success",
        historical_agreement_rate=1.0,  # deliberately favorable too
    )

    passed = risk.recommendation == "approval_required"
    return SafetyUnderMiscalibrationResult(
        scenario="Synthetic: AI proposes sending an interview invitation with 0.95 confidence, "
        "on a case constructed to represent a wrong decision.",
        forced_confidence=0.95,
        forced_decision_was_wrong=True,
        recommendation=risk.recommendation,
        gate_required=risk.recommendation in {"approval_required", "human_review", "automate_with_monitoring"},
        passed=passed,
        explanation=risk.reason,
    )
