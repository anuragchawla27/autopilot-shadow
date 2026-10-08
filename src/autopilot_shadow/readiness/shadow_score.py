"""
The Shadow Score (Day 13, Section 15) — a single headline number that
stays DECOMPOSABLE into the parts that produced it, per Section 15's
explicit requirement.

THE FORMULA (documented, equal weights — justified below, not asserted):

    shadow_score = 100 * mean(accuracy, human_agreement,
                               decision_stability, evidence_coverage)

- accuracy                = Day 5 reconstruction (mean of step/edge recall)
- human_agreement         = Day 9 (mean of the 5 separate dimensions)
- decision_stability      = Day 6, evidence-weighted grounded-rule ratio
- evidence_coverage       = Day 6, rule-count grounded-rule ratio

WEIGHT JUSTIFICATION: equal weights (0.25 each), for the same reason
Day 10's `risk_factors.impact_score` used a plain average for its 4
static factors (D-045/D-046's own precedent) — these four components
measure genuinely different things (can we even recover the workflow?
does the AI agree with humans? is the decision logic grounded in real
evidence, two different ways?) and this project has no comparative
experiment yet (that's Day 15) that would justify weighting one above
another. Documented as a revisitable starting point, exactly as
Section 15 requires ("the intern must define the formula... do not use
arbitrary weights without justification" — "equal, pending evidence" is
the justification here, the same one Day 10 gave for impact_score).

Risk and Reversibility are reported ALONGSIDE the score as their own
categorical fields (matching the brief's own example table exactly:
"Risk: Medium, Reversibility: High") — NOT folded into the 0-100
average, because they are not themselves success metrics, they are
safety context the reader needs next to the score.

HARD CAP (mirrors Day 10's hard-override pattern, D-047): if Section
29's false_automation_rate is ever > 0, the shadow score is capped at
49 regardless of what the 4 components say — a formula is not allowed
to average away an observed false automation, consistent with Section
29's instruction to prioritize this metric above raw coverage.
"""

from __future__ import annotations

from .metrics import (
    decision_extraction_quality,
    false_automation_rate,
    false_escalation_rate,
    human_ai_agreement,
    reconstruction_accuracy,
    risk_and_reversibility,
)

FALSE_AUTOMATION_HARD_CAP = 49.0


def compute_shadow_score() -> dict:
    accuracy = reconstruction_accuracy()
    agreement = human_ai_agreement()
    decision = decision_extraction_quality()
    risk = risk_and_reversibility()
    false_auto = false_automation_rate()
    false_esc = false_escalation_rate()

    components = {
        "accuracy": accuracy["combined"],
        "human_agreement": agreement["mean"],
        "decision_stability": decision["evidence_weighted_stability"],
        "evidence_coverage": decision["rule_coverage"],
    }
    raw_score = round(100 * sum(components.values()) / len(components), 2)

    capped = false_auto["false_automation_rate"] is not None and false_auto["false_automation_rate"] > 0.0
    final_score = min(raw_score, FALSE_AUTOMATION_HARD_CAP) if capped else raw_score

    return {
        "shadow_score": final_score,
        "raw_score_before_cap": raw_score,
        "hard_capped_by_false_automation": capped,
        "components": components,
        "risk": risk["risk_label"],
        "reversibility": risk["reversibility_label"],
        "reconstruction_accuracy": accuracy,
        "human_ai_agreement": agreement,
        "decision_extraction_quality": decision,
        "risk_and_reversibility": risk,
        "false_automation_rate": false_auto,
        "false_escalation_rate": false_esc,
    }
