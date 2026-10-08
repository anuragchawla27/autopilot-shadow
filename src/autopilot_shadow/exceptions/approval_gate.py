"""
Human-in-the-loop approval gates (Day 11, Section 18).

Section 18 requires exactly four possible outcomes a human can apply to
an AI-proposed action: APPROVE (execute as proposed), EDIT (modify the
proposed action), REJECT (discard it), ESCALATE (send to deeper human
review). This module models that gate as two separate, deliberately
small steps:

1. `gate_for(risk_score)` — decides whether a case needs a gate AT ALL,
   from Day 10's own recommendation. This is READ-ONLY: it never
   approves anything itself.
2. `apply_decision(...)` — the ONLY function in this codebase allowed to
   move an ApprovalState out of PENDING, and it always requires an
   explicit `decision` argument from outside. There is no code path
   that can set APPROVED without that argument being passed in by
   whoever is standing in for the human reviewer (today: a human
   literally typing the decision when this module's demo/tests call
   it; a real deployment would wire this to the Day 14 dashboard's
   button clicks, not to any part of this system itself).

SAFETY PROPERTY THIS IS BUILT TO GUARANTEE: nothing in `risk_model.py`,
`detector.py`, or `disagreement.py` ever produces an ApprovalState other
than NOT_REQUIRED or PENDING. APPROVED only exists as the result of
`apply_decision(..., decision="approve")` being called with that literal
argument — proven directly by `test_automated_recommendation_can_never_become_approved_state_on_its_own`,
which parses this module's own source and confirms `ApprovalState.APPROVED`
is assigned nowhere except inside `apply_decision`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

# Recommendations from Day 10's risk model that must stop at a gate before
# anything is treated as final. "automate" is the only one that does NOT.
GATE_REQUIRED_RECOMMENDATIONS = {"approval_required", "human_review", "automate_with_monitoring"}

Decision = Literal["approve", "edit", "reject", "escalate"]


@dataclass(frozen=True)
class ApprovalRequest:
    resume_id: Optional[str]
    action: str
    risk_score: float
    recommendation: str
    reason: str
    gate_required: bool


@dataclass(frozen=True)
class ApprovalOutcome:
    request: ApprovalRequest
    decision: Decision
    approval_state: str  # schemas.event.ApprovalState value
    edited_payload: Optional[dict]
    note: str


def gate_for(risk_score: dict) -> ApprovalRequest:
    """Builds a (read-only) approval request from one Day 10 risk score
    dict. Does NOT decide the outcome — only whether a gate applies."""
    recommendation = risk_score["recommendation"]
    return ApprovalRequest(
        resume_id=risk_score.get("resume_id"),
        action=risk_score["action"],
        risk_score=risk_score["risk_score"],
        recommendation=recommendation,
        reason=risk_score["reason"],
        gate_required=recommendation in GATE_REQUIRED_RECOMMENDATIONS,
    )


def apply_decision(
    request: ApprovalRequest,
    decision: Decision,
    edited_payload: Optional[dict] = None,
) -> ApprovalOutcome:
    """The only function that can turn a PENDING gate into a final
    ApprovalState. `decision` must be explicitly supplied by the
    caller — there is no default and no way to reach APPROVED without
    it. Matches Section 18's exact 4-state vocabulary."""
    if decision == "approve":
        state = "approved"
        note = "Human approved the AI-proposed action as-is."
    elif decision == "edit":
        if not edited_payload:
            raise ValueError("decision='edit' requires edited_payload describing what changed.")
        state = "edited"
        note = f"Human modified the proposed action: {edited_payload}"
    elif decision == "reject":
        state = "rejected"
        note = "Human discarded the AI-proposed action; it will not be executed."
    elif decision == "escalate":
        state = "escalated"
        note = "Sent to deeper human review."
    else:
        raise ValueError(f"Unknown decision {decision!r} — must be one of approve/edit/reject/escalate")

    return ApprovalOutcome(
        request=request,
        decision=decision,
        approval_state=state,
        edited_payload=edited_payload,
        note=note,
    )


def build_approval_queue(risk_scores: list[dict]) -> list[ApprovalRequest]:
    """Every case whose Day 10 recommendation requires a gate, in the
    order the risk scores were produced. This is the PENDING queue — no
    function here resolves any of them."""
    return [gate_for(s) for s in risk_scores if gate_for(s).gate_required]
