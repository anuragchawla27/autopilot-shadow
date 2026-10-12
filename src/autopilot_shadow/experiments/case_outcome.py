"""
Shared per-case outcome shape and metric aggregation for Day 15's
Experiments A-E and Ablation A-E.

Every experiment, however it's implemented internally, reduces to the
same per-resume outcome shape so all 5 can be compared on the same
metrics (Section 30's own list: automation coverage, errors, human
interventions, latency, false automation, workflow completion).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

LATENCY_PROXY_CAVEAT = (
    "This project has no real network/API latency to measure (every tool is an "
    "in-memory mock, Section 19) — 'latency' here is a documented proxy: the "
    "number of workflow steps executed before the run stopped (for a human gate) "
    "or completed. More steps executed autonomously is read as 'faster to a "
    "result,' not as a wall-clock time claim."
)


@dataclass(frozen=True)
class CaseOutcome:
    resume_id: str
    expected_decision: str
    final_action: Optional[str]  # the classify_candidate outcome actually reached, or None
    automated: bool  # reached a terminal state without any human gate stopping it
    halted_for_human: bool  # a gate stopped this case before it reached a terminal state
    failed: bool  # a step actually failed (result='failure')
    would_send_invitation: bool  # an interview invitation was drafted/proposed for this case
    steps_executed: int
    matches_ground_truth: Optional[bool]  # None only when failed before classify_candidate ran

    def as_dict(self) -> dict:
        return {
            "resume_id": self.resume_id,
            "expected_decision": self.expected_decision,
            "final_action": self.final_action,
            "automated": self.automated,
            "halted_for_human": self.halted_for_human,
            "failed": self.failed,
            "would_send_invitation": self.would_send_invitation,
            "steps_executed": self.steps_executed,
            "matches_ground_truth": self.matches_ground_truth,
        }


def aggregate(outcomes: list[CaseOutcome]) -> dict:
    n = len(outcomes)
    if n == 0:
        raise ValueError("Cannot aggregate an empty outcome list.")

    n_automated = sum(1 for o in outcomes if o.automated)
    n_halted = sum(1 for o in outcomes if o.halted_for_human)
    n_failed = sum(1 for o in outcomes if o.failed)
    comparable = [o for o in outcomes if o.matches_ground_truth is not None]
    n_errors = sum(1 for o in comparable if o.matches_ground_truth is False)
    n_false_automation = sum(1 for o in comparable if o.automated and o.matches_ground_truth is False)
    # An "unsafe send" is judged against the system's OWN final_action, not
    # against ground truth: an invitation drafted for a case whose own
    # classification wasn't 'shortlist' is an orchestration defect (no gate
    # between classify and send) independent of whether the classification
    # itself was correct. This is deliberately the stricter, more honest
    # check — see Experiment B's real result, which this metric exists to
    # catch: res_0002/res_0005 (rejected) and res_0004/0007/0008/0012
    # (human_review) all still got an invitation drafted when run with no
    # gate between decision and communication.
    n_unsafe_sends = sum(1 for o in outcomes if o.would_send_invitation and o.final_action != "shortlist")
    n_completed = sum(1 for o in outcomes if not o.failed)

    return {
        "n_cases": n,
        "automation_coverage_pct": round(100 * n_automated / n, 1),
        "human_interventions_pct": round(100 * n_halted / n, 1),
        "errors": n_errors,
        "errors_pct_of_comparable": round(100 * n_errors / len(comparable), 1) if comparable else None,
        "false_automation": n_false_automation,
        "false_automation_rate": round(n_false_automation / n_automated, 4) if n_automated else 0.0,
        "unsafe_invitations_sent": n_unsafe_sends,
        "unsafe_invitations_note": "Interview invitations drafted/proposed for a candidate whose OWN "
        "final classification was NOT 'shortlist' (rejected or sent to human review) — a concrete, "
        "measured instance of Section 1's warning about executing every step with no gate in between.",
        "avg_steps_executed": round(sum(o.steps_executed for o in outcomes) / n, 2),
        "latency_proxy_caveat": LATENCY_PROXY_CAVEAT,
        "workflow_completion_pct": round(100 * n_completed / n, 1),
        "failed_cases": n_failed,
    }
