"""
Workflow reconstruction engine (Day 5).

Takes the raw event log (Day 4's demonstrations.json — many separate
demo runs of the same workflow) and produces ONE structured Workflow
(Day 2 schema): the canonical sequence of steps, with branches where
demonstrations diverge.

This is Section 6 of the brief: "transform raw workflow demonstrations
into a structured workflow" by identifying relationships between events.

WHAT THIS STAGE DOES NOT DO (by design, see docs/03):
- It does NOT classify steps into automate/human_review/etc. — that is
  the automation generator's job (Day 7), which needs explicit criteria
  we haven't built yet.
- It does NOT label rules explicit/inferred/unknown — that is decision
  extraction's job (Day 6).
- It does NOT compute risk. That is Day 10.
Every WorkflowStep produced here has step_type=UNCLASSIFIED and
risk=UNKNOWN on purpose; a later stage fills them in, and we can always
tell "not yet classified" apart from "classified as unclear" this way.

ALGORITHM (our own engineering design — not a claim of prior art):
1. Group events by demo_id, in step_index order — this recovers each
   demonstration's own local sequence.
2. Walk all demonstrations "in lockstep" by ACTION NAME rather than by
   position: build a directed graph where an edge action_A -> action_B
   exists whenever B was the event that followed A within the same demo.
   Failed events (result == "failure") end a demo's contribution to the
   graph at that point — a demo that failed on step 2 can never imply an
   edge to steps 3+, matching what actually happened.
3. Each distinct action name becomes exactly one WorkflowStep (so
   'classify_candidate' from 12 different demos becomes ONE node, not
   12) — this is what makes the result a structured workflow rather
   than just a replay of the logs.
4. A node with more than one outgoing edge is a branch: its next_steps
   lists every action that was ever observed to follow it.
5. The step's `application` is taken from the most common application
   value seen for that action across demos (majority vote) — logged
   as a simple, auditable rule rather than an opaque model.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from autopilot_shadow.schemas.workflow import RiskLevel, StepType, Workflow, WorkflowStep


def filter_structural_demos(events: list[dict], exclude_prefixes: tuple[str, ...] = ("demo_dup_", "demo_fault_")) -> list[dict]:
    """Excludes the deliberately-artificial duplicate/fault demonstrations
    from Day 4 (demo_dup_*, demo_fault_*) before structural reconstruction.

    WHY: those demos exist to exercise exception handling (Day 11) and
    contain events that don't reflect normal workflow shape — e.g. the
    duplicate-fetch demo appends an extra fetch_resume call AFTER a
    completed run, which would otherwise create a nonsensical edge
    (send_interview_invitation -> fetch_resume) in the reconstructed
    graph. Reconstruction should learn workflow STRUCTURE from organic
    demonstrations; exception paths are handled explicitly elsewhere.
    This filter is applied here, visibly, rather than silently — see
    decision D-022.
    """
    return [e for e in events if not any(e["demo_id"].startswith(p) for p in exclude_prefixes)]


def _group_by_demo(events: list[dict]) -> dict[str, list[dict]]:
    by_demo: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        by_demo[e["demo_id"]].append(e)
    for demo_id in by_demo:
        by_demo[demo_id].sort(key=lambda e: e["step_index"])
    return by_demo


def reconstruct_workflow(events: list[dict], workflow_name: str, workflow_id: str) -> Workflow:
    """Builds one Workflow from a flat list of serialized Events (as
    produced by build_dataset.py / EventLogger.model_dump)."""

    by_demo = _group_by_demo(events)

    # action -> Counter(application -> count), for majority-vote application
    action_applications: dict[str, Counter] = defaultdict(Counter)
    # action -> set of actions that immediately followed it (across all demos)
    edges: dict[str, set[str]] = defaultdict(set)
    # action -> True if this action was ever the very first step of a demo
    entry_candidates: set[str] = set()
    # preserve first-seen order for deterministic step ids
    action_order: list[str] = []
    seen_actions: set[str] = set()

    demo_ids_used: list[str] = []

    for demo_id, demo_events in by_demo.items():
        demo_ids_used.append(demo_id)
        if not demo_events:
            continue

        entry_candidates.add(demo_events[0]["action"])

        prev_action: str | None = None
        for evt in demo_events:
            action = evt["action"]
            if action not in seen_actions:
                seen_actions.add(action)
                action_order.append(action)
            action_applications[action][evt.get("application") or "unknown"] += 1

            if prev_action is not None:
                edges[prev_action].add(action)

            if evt["result"] == "failure":
                # this demo stops contributing edges beyond a failure —
                # mirrors the fact that nothing observably happened after it
                prev_action = None
                break
            prev_action = action

    # entry step = the action most demos actually started with (majority vote)
    entry_counter = Counter()
    for demo_id, demo_events in by_demo.items():
        if demo_events:
            entry_counter[demo_events[0]["action"]] += 1
    entry_action = entry_counter.most_common(1)[0][0] if entry_counter else (action_order[0] if action_order else None)

    if entry_action is None:
        raise ValueError("No events supplied — cannot reconstruct a workflow with zero demonstrations.")

    steps: list[WorkflowStep] = []
    action_to_step_id = {action: f"step_{i+1}" for i, action in enumerate(action_order)}

    for action in action_order:
        step_id = action_to_step_id[action]
        next_actions = sorted(edges.get(action, set()))
        top_application = action_applications[action].most_common(1)[0][0]

        steps.append(
            WorkflowStep(
                id=step_id,
                name=action,
                description=f"Reconstructed from {sum(action_applications[action].values())} observed occurrence(s) across demonstrations.",
                next_steps=[action_to_step_id[a] for a in next_actions],
                application=None if top_application == "unknown" else top_application,
                action=action,
                step_type=StepType.UNCLASSIFIED,
                risk=RiskLevel.UNKNOWN,
                classification_reason=None,
            )
        )

    return Workflow(
        workflow_id=workflow_id,
        workflow_name=workflow_name,
        version=1,
        version_label="manual",
        entry_step_id=action_to_step_id[entry_action],
        steps=steps,
        source_demo_ids=demo_ids_used,
    )


def reconstruction_stats(workflow: Workflow, events: list[dict]) -> dict[str, Any]:
    """Simple, auditable stats about the reconstruction — used for the
    Day 5 proof and later folded into the readiness evaluation (Day 13)."""
    by_demo = _group_by_demo(events)
    branch_steps = [s.id for s in workflow.steps if len(s.next_steps) > 1]
    return {
        "num_demonstrations": len(by_demo),
        "num_events": len(events),
        "num_distinct_steps": len(workflow.steps),
        "num_branch_steps": len(branch_steps),
        "branch_step_ids": branch_steps,
        "entry_step_id": workflow.entry_step_id,
    }
