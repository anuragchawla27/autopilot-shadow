"""
Reconstruction accuracy evaluation (Section 27: "Can the system recover
the correct sequence?").

The expected canonical sequence is Section 5 of the brief, verbatim:
    receive resume -> extract info -> check experience -> compare skills
    -> mark shortlisted -> update record -> send interview invitation

Mapped to our action names:
    fetch_resume -> extract_resume -> check_experience -> compare_skills
    -> classify_candidate -> update_candidate_record -> send_interview_invitation

We score two things, both computed from the actual reconstructed
Workflow object (never hand-typed, per S7):
  1. Step recall: are all 7 expected actions present as steps?
  2. Edge precision/recall on the canonical happy-path transitions.
"""

from __future__ import annotations

from autopilot_shadow.schemas.workflow import Workflow

EXPECTED_SEQUENCE = [
    "fetch_resume",
    "extract_resume",
    "check_experience",
    "compare_skills",
    "classify_candidate",
    "update_candidate_record",
    "send_interview_invitation",
]

EXPECTED_EDGES = list(zip(EXPECTED_SEQUENCE[:-1], EXPECTED_SEQUENCE[1:]))


def evaluate_reconstruction(workflow: Workflow) -> dict:
    step_names = {s.name for s in workflow.steps}
    steps_by_name = {s.name: s for s in workflow.steps}

    present = [a for a in EXPECTED_SEQUENCE if a in step_names]
    missing = [a for a in EXPECTED_SEQUENCE if a not in step_names]
    step_recall = len(present) / len(EXPECTED_SEQUENCE)

    edge_hits = 0
    edge_misses = []
    for src, dst in EXPECTED_EDGES:
        src_step = steps_by_name.get(src)
        dst_step_id = None
        if dst in steps_by_name:
            dst_step_id = steps_by_name[dst].id
        if src_step is not None and dst_step_id is not None and dst_step_id in src_step.next_steps:
            edge_hits += 1
        else:
            edge_misses.append((src, dst))
    edge_recall = edge_hits / len(EXPECTED_EDGES)

    return {
        "expected_steps": EXPECTED_SEQUENCE,
        "steps_present": present,
        "steps_missing": missing,
        "step_recall": round(step_recall, 4),
        "expected_edges": EXPECTED_EDGES,
        "edge_hits": edge_hits,
        "edge_total": len(EXPECTED_EDGES),
        "edge_recall": round(edge_recall, 4),
        "edge_misses": edge_misses,
    }
