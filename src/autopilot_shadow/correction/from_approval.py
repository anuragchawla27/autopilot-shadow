"""
Builds a Section-24 CorrectionRecord from a Day 11 ApprovalOutcome
(the result of `exceptions.approval_gate.apply_decision`).

A "correction" is specifically what Section 24 describes: a human
changing what the AI proposed. `decision == "approve"` means the human
agreed with the AI as-is — that's not a correction, so this module
refuses to build a record for it (returns None), keeping the store
honest about what it actually contains.
"""

from __future__ import annotations

import uuid
from typing import Optional

from autopilot_shadow.exceptions.approval_gate import ApprovalOutcome

from .schema import CorrectionRecord, now_iso

CORRECTION_DECISIONS = {"edit", "reject", "escalate"}


def correction_from_outcome(
    outcome: ApprovalOutcome,
    workflow_name: str = "resume_screening",
    reason: Optional[str] = None,
    source: str = "human_review",
) -> Optional[CorrectionRecord]:
    """Returns None for decision == 'approve' (not a correction). For
    edit/reject/escalate, builds the full Section-24 record from the
    ApprovalRequest/ApprovalOutcome already computed by Day 10/11 —
    nothing here recomputes risk or confidence."""
    if outcome.decision not in CORRECTION_DECISIONS:
        return None

    req = outcome.request
    return CorrectionRecord(
        correction_id=f"corr_{uuid.uuid4().hex[:8]}",
        workflow_context={"workflow": workflow_name, "resume_id": req.resume_id, "action": req.action},
        original_ai_decision={
            "recommendation": req.recommendation,
            "risk_score": req.risk_score,
            "reason": req.reason,
        },
        human_correction=outcome.decision,
        human_correction_detail={
            "approval_state": outcome.approval_state,
            "edited_payload": outcome.edited_payload,
            "note": outcome.note,
        },
        evidence={"recommendation_that_was_overridden": req.recommendation, "risk_score": req.risk_score},
        reason=reason or f"Human chose '{outcome.decision}' over the AI's '{req.recommendation}' recommendation.",
        timestamp=now_iso(),
        source=source,
    )
