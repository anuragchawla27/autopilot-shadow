"""
Builds the correction memory store from Day 11's real approval queue.

HONEST CAVEAT — READ BEFORE TRUSTING ANY NUMBER THIS SCRIPT PRINTS:
This project has no live human-in-the-loop UI yet (that's Day 14's
dashboard). Nobody has actually clicked approve/edit/reject/escalate on
a real case. So there is currently no genuine Section-24 correction
data to store. Reporting "0 real corrections" would be the honest
finding (same pattern as Day 9's 0 disagreements, Day 11's 0
disagreement records) — but it would also leave the storage/retrieval
mechanism completely unexercised against real queue data, not just
hand-built test fixtures.

So this script applies a small, FIXED, DETERMINISTIC reference policy
(`simulate_decision`, defined right here, not hidden) to Day 11's real
16-item approval queue, clearly tagged `source="simulated_demo"` on
every record it writes. This is a DEMONSTRATION of the mechanism
working end-to-end against real queue shapes, NOT an evaluation result
and NOT real human correction data. It must never be read as, or cited
as, an actual human-agreement or correction-rate metric — the test
suite's hand-built synthetic cases (same pattern as Days 9 and 11) are
what prove the storage/retrieval logic itself is correct;
this script only proves it runs against real inputs without crashing
and produces sensible, honestly-labeled output.

Run: python -m autopilot_shadow.correction.build_correction_memory
"""

from __future__ import annotations

import json
from pathlib import Path

from autopilot_shadow.exceptions.approval_gate import ApprovalRequest, apply_decision

from .from_approval import correction_from_outcome
from .memory import CorrectionMemory

ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = ROOT / "results"


def simulate_decision(request: ApprovalRequest) -> tuple[str, dict | None]:
    """The fixed reference policy used ONLY to demonstrate the pipeline
    against real queue data — see module docstring. Not a learned
    policy, not real human judgment."""
    if request.recommendation == "approval_required":
        # Section 22: never auto-approve an irreversible external action, even here.
        return "escalate", None
    if request.recommendation == "human_review":
        # The underlying data was unusable (a failed extraction) — nothing to approve.
        return "reject", None
    if request.recommendation == "automate_with_monitoring":
        return "edit", {"monitoring_note": "Approved with an added manual spot-check on the resulting CRM entry."}
    # Anything else reaching here would mean gate_for let an 'automate' case through, which
    # build_approval_queue's own filter already prevents.
    raise ValueError(f"simulate_decision called on an unexpected recommendation: {request.recommendation!r}")


def main() -> None:
    queue_data = json.loads((RESULTS_DIR / "day11_approval_queue.json").read_text())
    memory = CorrectionMemory()

    for q in queue_data:
        request = ApprovalRequest(**q)
        decision, edited_payload = simulate_decision(request)
        outcome = apply_decision(request, decision, edited_payload=edited_payload)
        record = correction_from_outcome(
            outcome,
            reason=f"[SIMULATED DEMO] reference policy applied '{decision}' to a '{request.recommendation}' case.",
            source="simulated_demo",
        )
        if record is not None:  # always true here since simulate_decision never returns "approve"
            memory.add(record)

    RESULTS_DIR.mkdir(exist_ok=True)
    memory.save(RESULTS_DIR / "day12_correction_memory.json")

    print(f"[SIMULATED DEMO — see module docstring] Stored {len(memory.all())} correction records "
          f"from {len(queue_data)} real Day 11 approval-queue items.\n")
    print("Correction count by action:")
    for action, stats in sorted(memory.correction_rate_by_action().items()):
        print(f"  {action:<28} {stats['correction_count']}")

    print("\nWrote: results/day12_correction_memory.json")


if __name__ == "__main__":
    main()
