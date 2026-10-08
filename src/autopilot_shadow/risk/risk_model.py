"""
Risk model (Day 10, Section 10) — combines static action factors,
per-case confidence, and historical agreement into one risk score and
recommendation, per case, replacing Day 8's placeholder confidence-only
model.

WHY THIS IS DIFFERENT FROM DAY 7's CLASSIFICATION:
Day 7's `classifier.py` assigns one step_type per STEP (e.g. every
classify_candidate case gets the same category) based on what rules are
attached in general. Section 10 asks for something finer: a score that
can differ CASE BY CASE, because a specific case's confidence differs
(D-033's deferred honest finding — res_0001's clean explicit-rule match
and res_0004's ambiguous unknown-rule case both halt at the same STEP
under Day 7's model, but they are not equally risky cases, and Section
10 is where that distinction finally gets made).

THE FORMULA (documented, not arbitrary — Section 10's explicit
requirement):

  risk_score = 0.5 * impact_score + 0.3 * uncertainty + 0.2 * disagreement

  impact_score   (risk_factors.py)  — static per-action factors (reversibility,
                                       external-facing, financial impact, privacy)
  uncertainty    = 1 - confidence    — THIS case's AI confidence (Day 6/8)
  disagreement   = 1 - historical_agreement_rate(action) — Day 9, per action

WEIGHT JUSTIFICATION:
- impact_score gets the largest weight (0.5) because it reflects what the
  action itself could do if it goes wrong, independent of how confident
  the AI happens to feel about this one case — Section 22's safety
  framing treats impact as the thing that must never be diluted away by
  a confident-sounding model.
- uncertainty gets the next weight (0.3) because it is a genuine,
  case-specific signal: how well does THIS case fit the rules we've
  actually extracted (Day 6)?
- disagreement gets the smallest weight (0.2) DELIBERATELY, because
  Day 9/`historical_agreement.py` documents that the real dataset's
  historical-agreement signal is inflated (same author wrote both
  sides) — giving it equal or higher weight would let an artificially
  perfect number pull risk scores down further than the evidence
  actually supports.

These weights are a documented starting point, explicitly expected to
be revisited once Day 15's experiments (A-E) and ablations exist to
justify different ones with real comparative evidence — not asserted as
final.

HARD OVERRIDE (Section 22, matches Day 7 Criterion 1):
An irreversible + external-facing action ALWAYS requires explicit human
approval, regardless of how low its computed score is. No formula is
allowed to automate away Section 22's hard safety case.

FAILED-STEP OVERRIDE (bug caught while building this — see docs/12):
A step that actually FAILED (`result == "failure"`) is forced to
HUMAN_REVIEW regardless of its nominal confidence. Day 8's shadow
executor logs `confidence=0.99` on extract_resume even when that very
call failed (0.99 is the fixed "deterministic step" confidence — it
describes how much judgment the COMPUTATION involves, not whether it
actually succeeded). Scoring a failed step by its nominal confidence
would treat "the system doesn't even have usable data" as if it were a
simple, high-confidence automate case — exactly backwards.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .risk_factors import ACTION_RISK_FACTORS, impact_score

IMPACT_WEIGHT = 0.5
UNCERTAINTY_WEIGHT = 0.3
DISAGREEMENT_WEIGHT = 0.2

RECOMMENDATION_THRESHOLDS = (
    (0.25, "automate"),
    (0.50, "automate_with_monitoring"),
    (0.75, "human_review"),
    (1.01, "blocked"),  # catches everything up to and including 1.0
)


@dataclass(frozen=True)
class RiskScore:
    action: str
    resume_id: Optional[str]
    confidence: Optional[float]
    impact_score: float
    uncertainty: Optional[float]
    disagreement: Optional[float]
    historical_agreement_rate: Optional[float]
    risk_score: float
    recommendation: str
    reason: str

    def as_dict(self) -> dict:
        return {
            "action": self.action,
            "resume_id": self.resume_id,
            "confidence": self.confidence,
            "impact_score": self.impact_score,
            "uncertainty": self.uncertainty,
            "disagreement": self.disagreement,
            "historical_agreement_rate": self.historical_agreement_rate,
            "risk_score": self.risk_score,
            "recommendation": self.recommendation,
            "reason": self.reason,
        }


def _recommendation_for_score(score: float) -> str:
    for threshold, label in RECOMMENDATION_THRESHOLDS:
        if score < threshold:
            return label
    return "blocked"  # unreachable given the 1.01 sentinel, kept for safety


def score_case(
    action: str,
    resume_id: Optional[str],
    confidence: Optional[float],
    result: str,
    historical_agreement_rate: Optional[float],
) -> RiskScore:
    """Scores one AI-proposed action for one case. `confidence` and
    `result` come from the Day 8 shadow event; `historical_agreement_rate`
    comes from `historical_agreement.per_action_agreement` (Day 9 data).
    """
    factors = ACTION_RISK_FACTORS.get(action)
    if factors is None:
        raise KeyError(f"No risk factors defined for action {action!r} — risk_factors.py must cover every action")

    imp = impact_score(factors)

    # Hard safety override — Section 22 / Day 7 Criterion 1.
    if not factors.reversible and factors.external_facing:
        return RiskScore(
            action=action,
            resume_id=resume_id,
            confidence=confidence,
            impact_score=imp,
            uncertainty=None,
            disagreement=None,
            historical_agreement_rate=historical_agreement_rate,
            risk_score=1.0,
            recommendation="approval_required",
            reason="HARD OVERRIDE (Section 22): irreversible + external-facing action always requires "
            "explicit human approval, regardless of confidence or historical agreement.",
        )

    # Failed-step override — a nominal confidence doesn't describe a failed execution.
    if result == "failure":
        return RiskScore(
            action=action,
            resume_id=resume_id,
            confidence=confidence,
            impact_score=imp,
            uncertainty=None,
            disagreement=None,
            historical_agreement_rate=historical_agreement_rate,
            risk_score=1.0,
            recommendation="human_review",
            reason="OVERRIDE: this step's execution failed (result='failure') — its nominal confidence "
            "describes the computation's judgment level, not whether it actually succeeded. A failed "
            "step cannot be scored as a confident automate case.",
        )

    if confidence is None:
        raise ValueError(f"confidence is required to score a non-failed, non-overridden case ({action}, {resume_id})")

    uncertainty = round(1 - confidence, 4)
    disagreement = round(1 - historical_agreement_rate, 4) if historical_agreement_rate is not None else uncertainty
    note = "" if historical_agreement_rate is not None else " (no historical agreement data for this action — used uncertainty as a substitute)"

    risk = round(IMPACT_WEIGHT * imp + UNCERTAINTY_WEIGHT * uncertainty + DISAGREEMENT_WEIGHT * disagreement, 4)
    recommendation = _recommendation_for_score(risk)

    return RiskScore(
        action=action,
        resume_id=resume_id,
        confidence=confidence,
        impact_score=imp,
        uncertainty=uncertainty,
        disagreement=disagreement,
        historical_agreement_rate=historical_agreement_rate,
        risk_score=risk,
        recommendation=recommendation,
        reason=f"risk = {IMPACT_WEIGHT}*impact({imp}) + {UNCERTAINTY_WEIGHT}*uncertainty({uncertainty}) + "
        f"{DISAGREEMENT_WEIGHT}*disagreement({disagreement}) = {risk}{note}",
    )
