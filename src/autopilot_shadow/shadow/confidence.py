"""
Provisional shadow-mode confidence scoring (Day 8).

Section 12 requires every shadow-proposed action to record a confidence
value. The REAL confidence/risk model (reversibility, external impact,
financial impact, privacy, uncertainty, historical agreement,
authorization — Section 10) is Day 10's job. This file is a SMALL,
PROVISIONAL placeholder, exactly like generator/risk_profile.py was for
Day 7 — just enough for Day 8's records to be meaningful, explicitly
documented as provisional, and designed to be replaced (not quietly kept)
on Day 10.

DESIGN: confidence is tied to the SPECIFIC rule evidence behind THIS
case's decision, not a flat per-step number. For classify_candidate, we
find which of Day 6's extracted Rules actually matches this case's
evidence (experience_ok, skill_match_tier, injection_detected) and
derive confidence from that rule's type:
  EXPLICIT -> 0.95 (backed by stated configuration)
  INFERRED -> 0.75 (consistent pattern, 2+ examples)
  UNKNOWN  -> 0.40 (insufficient/contradictory evidence)
  no matching rule found -> 0.30 (a case unlike anything seen before)

For pure data steps (fetch/extract/check_experience) with no judgment
involved, confidence is fixed at 0.99 — deterministic computation, not a
business decision.
"""

from __future__ import annotations

from autopilot_shadow.common.rule_evaluation import rule_matches
from autopilot_shadow.schemas.workflow import RuleType, WorkflowStep

DETERMINISTIC_STEP_CONFIDENCE = 0.99

_RULE_TYPE_CONFIDENCE = {
    RuleType.EXPLICIT: 0.95,
    RuleType.INFERRED: 0.75,
    RuleType.UNKNOWN: 0.40,
}
NO_MATCHING_RULE_CONFIDENCE = 0.30


def confidence_for_decision_step(step: WorkflowStep, case_context: dict, actual_outcome: str) -> tuple[float, str]:
    """Returns (confidence, explanation) for a step that has Day 6 rules
    attached, by finding rules whose conditions actually evaluate true
    against this case's full context (operator-aware — see
    common/rule_evaluation.py) AND whose `then_outcome` matches the
    decision actually made (`actual_outcome`).

    WHY FILTER BY ACTUAL OUTCOME (bug caught while testing Day 8): more
    than one extracted rule can have its conditions satisfied by the
    same case — e.g. a prompt-injection resume that also happens to
    have a full skill match satisfies BOTH the explicit full-match rule
    (which implies 'shortlist' and knows nothing about injection) AND
    the injection-specific rule (which implies 'human_review'). Picking
    whichever rule happened to be checked first gave a confidently wrong
    answer: 0.95 confidence for a decision the matched rule didn't
    actually predict. Grounding confidence in "which rule explains the
    decision that was ACTUALLY made" is the only version of this that
    is honest and useful for Day 10/13's readiness scoring.

    `case_context` must include every raw field any attached rule might
    reference (experience_years, required_skills_present, experience_ok,
    skill_match_tier, injection_detected) — see shadow_executor.py's
    case-context construction.
    """
    matching_rules = [r for r in step.rules if rule_matches(r, case_context)]
    explaining_rules = [r for r in matching_rules if r.then_outcome == actual_outcome]

    if explaining_rules:
        # Prefer the strongest-evidence rule_type among those that actually explain the outcome.
        best = min(explaining_rules, key=lambda r: list(_RULE_TYPE_CONFIDENCE).index(r.rule_type))
        conf = _RULE_TYPE_CONFIDENCE[best.rule_type]
        note = ""
        if len(matching_rules) > len(explaining_rules):
            other_outcomes = sorted({r.then_outcome for r in matching_rules if r.then_outcome != actual_outcome})
            note = f" (NOTE: {len(matching_rules) - len(explaining_rules)} other matching rule(s) implied a different outcome: {other_outcomes} — the actual decision was used to disambiguate)"
        return conf, f"Matched rule {best.rule_id} ({best.rule_type.value}): {best.description}{note}"

    return (
        NO_MATCHING_RULE_CONFIDENCE,
        f"No extracted rule both matches this case's context {case_context} AND explains the actual "
        f"outcome {actual_outcome!r} — unlike anything seen in the 12 demonstrations.",
    )


def confidence_for_deterministic_step() -> tuple[float, str]:
    return DETERMINISTIC_STEP_CONFIDENCE, "Deterministic computation (no business judgment involved)."
