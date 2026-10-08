"""
Automation readiness decision (Day 13, Section 26): NOT_READY,
PARTIALLY_READY, HUMAN_IN_THE_LOOP_READY, or HIGH_AUTOMATION_READINESS.

DECISION LOGIC (ordered checks, documented thresholds — not arbitrary):

1. Section 29 is explicit that false automation is disqualifying above
   everything else: ANY observed false_automation_rate > 0 forces
   NOT_READY, no matter how good the other numbers look.
2. evidence_coverage < 0.25 (fewer than a quarter of extracted rules
   are grounded, explicit/inferred) means the decision logic mostly
   rests on single-example guesses — NOT_READY on insufficient evidence
   (Section 26's own category label).
3. HIGH_AUTOMATION_READINESS requires BOTH evidence_coverage >= 0.85
   AND `independent_evaluation=True`. The second condition is a HARD
   GATE, not a number: this project's human-agreement figures come from
   a human policy and an AI implementation written by the SAME author
   from the SAME rules (Day 9/D-043, Day 11/D-054) — no real
   independent human judgment has ever been exercised against this
   system. Claiming "high automation readiness" from numbers that
   cannot distinguish real agreement from shared-authorship coincidence
   would be exactly the kind of fabricated-confidence claim Section 38
   forbids. This gate stays False until real, independently-sourced
   human decisions exist to evaluate against.
4. Otherwise: if Day 11's approval gates are operational (they are,
   and tested — Section 18), the AI already prepares decisions that a
   human approves for anything outside the clean automate cases, which
   is Section 26's own definition of HUMAN_IN_THE_LOOP_READY.
5. Fallback: PARTIALLY_READY (low-risk steps automatable; no working
   human-in-the-loop gate for the rest — not this project's actual
   state today, since Day 11 built one, but the category remains
   reachable if `gates_operational` were ever False).
"""

from __future__ import annotations

from dataclasses import dataclass

EVIDENCE_COVERAGE_NOT_READY_CEILING = 0.25
EVIDENCE_COVERAGE_HIGH_READINESS_FLOOR = 0.85

# HARD GATE — see module docstring point 3. Flip only when real,
# independently-sourced human decisions exist to evaluate against.
INDEPENDENT_EVALUATION = False


@dataclass(frozen=True)
class ReadinessDecision:
    tier: str
    reason: str


def decide_readiness(
    evidence_coverage: float,
    false_automation_rate: float | None,
    gates_operational: bool,
    independent_evaluation: bool = INDEPENDENT_EVALUATION,
) -> ReadinessDecision:
    if false_automation_rate is not None and false_automation_rate > 0.0:
        return ReadinessDecision(
            tier="NOT_READY",
            reason=f"Section 29 hard rule: observed false_automation_rate={false_automation_rate} > 0 — "
            "at least one case recommended 'automate' did not match the human decision.",
        )

    if evidence_coverage < EVIDENCE_COVERAGE_NOT_READY_CEILING:
        return ReadinessDecision(
            tier="NOT_READY",
            reason=f"evidence_coverage={evidence_coverage} is below {EVIDENCE_COVERAGE_NOT_READY_CEILING} — "
            "too much of the decision logic rests on single-example (UNKNOWN) rules to trust.",
        )

    if evidence_coverage >= EVIDENCE_COVERAGE_HIGH_READINESS_FLOOR and independent_evaluation:
        return ReadinessDecision(
            tier="HIGH_AUTOMATION_READINESS",
            reason=f"evidence_coverage={evidence_coverage} >= {EVIDENCE_COVERAGE_HIGH_READINESS_FLOOR} and "
            "agreement has been checked against independently-sourced human decisions.",
        )

    if gates_operational:
        return ReadinessDecision(
            tier="HUMAN_IN_THE_LOOP_READY",
            reason="No false automation observed; low-risk steps automate directly; Day 11's tested "
            "approval gates (Section 18) let the AI prepare every other decision for human approval. "
            f"evidence_coverage={evidence_coverage} is not yet high enough, or human-agreement data is not "
            f"yet independently sourced (independent_evaluation={independent_evaluation}), for the HIGH tier.",
        )

    return ReadinessDecision(
        tier="PARTIALLY_READY",
        reason="No false automation observed and low-risk steps can be automated, but no working "
        "human-in-the-loop approval mechanism is in place for the rest.",
    )
