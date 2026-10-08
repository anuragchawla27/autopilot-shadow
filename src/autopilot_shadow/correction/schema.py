"""
Correction record schema (Day 12, Section 24).

Section 24 names the exact fields to store: "Original AI Decision,
Human Correction, Evidence, Workflow Context, Reason, Timestamp." This
module is that record, nothing more — Section 24 also explicitly warns
"Do not blindly retrain a model on every correction," so this is
deliberately just a structured, retrievable store, not a training
pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass(frozen=True)
class CorrectionRecord:
    correction_id: str
    workflow_context: dict  # {"workflow": ..., "resume_id": ..., "action": ...}
    original_ai_decision: dict  # Day 10's recommendation + risk_score + reason for this case
    human_correction: str  # "edit" | "reject" | "escalate" (never "approve" — that's not a correction)
    human_correction_detail: dict  # the ApprovalOutcome's approval_state, edited_payload, note
    evidence: dict
    reason: str
    timestamp: str  # ISO 8601, UTC
    source: str  # "simulated_demo" | "human_review" — see build_correction_memory.py's honest caveat

    def as_dict(self) -> dict:
        return {
            "correction_id": self.correction_id,
            "workflow_context": self.workflow_context,
            "original_ai_decision": self.original_ai_decision,
            "human_correction": self.human_correction,
            "human_correction_detail": self.human_correction_detail,
            "evidence": self.evidence,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "source": self.source,
        }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
