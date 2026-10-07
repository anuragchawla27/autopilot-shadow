"""
Human-AI comparison engine (Day 9, Sections 13-14).

Reads Day 4's human demonstration events (data/demonstrations.json) and
Day 8's AI shadow events (data/shadow_run.json), aligns them by
(resume_id, action), and produces a per-step comparison record matching
Section 13's table shape (Human Action, AI Action, Match/Mismatch,
Confidence, Evidence, Risk, Explanation).

KEY DESIGN CHALLENGE — DIFFERENT EVENT SHAPES FOR THE SAME ACTION:
Human events (Day 4) are real mock-tool calls with real output shapes
(e.g. a CRM record with `status`/`notes`/`history`). AI shadow events
(Day 8) are proposal-only and use different field names for the same
concept (e.g. `would_set_status` instead of `status`, because nothing
was actually written). Comparing these naively (raw dict equality) would
report false mismatches on every single step. `_normalize_step_value`
below maps each action's raw output into a small canonical form so
comparisons are semantically meaningful.

KEY DESIGN CHALLENGE — DIFFERENT EVENT COUNTS FOR THE SAME RESUME:
Day 4's human demo policy only logs a `send_interview_invitation` event
AT ALL if the candidate was shortlisted (see logger/human_demo.py) — a
rejected candidate's trace simply ends at update_candidate_record, 6
events long. Day 8's shadow executor, by contrast, ALWAYS walks the full
graph and logs a `send_interview_invitation` event for every case, even
when it proposes no action (would_send=False) — a rejected candidate's
shadow trace is 7 events long. This is a genuine, documented difference
in EVENT-LOGGING GRANULARITY between the two sources, not a workflow
disagreement: both sides agree no email should go out, one simply
didn't bother recording a no-op step. See `_align_steps` for how this
is detected and handled (flagged, not silently mismatched) — and
docs/11 for the full writeup, including why a naive comparison would
have gotten this wrong.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional


def _group_by_resume(events: list[dict], demo_id_to_resume_id) -> dict[str, list[dict]]:
    by_resume: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        resume_id = demo_id_to_resume_id(e["demo_id"])
        if resume_id is None:
            continue
        by_resume[resume_id].append(e)
    for resume_id in by_resume:
        by_resume[resume_id].sort(key=lambda e: e["step_index"])
    return by_resume


def human_resume_id_from_demo_id(demo_id: str) -> Optional[str]:
    """Only the 12 plain per-resume demos (demo_0001_res_0001, etc.) are
    used for comparison — the artificial demo_dup_*/demo_fault_* demos
    from Day 4 exist to test exception handling, not to represent a
    normal workflow run comparable to a shadow run (same reasoning as
    Day 5's reconstruction filter, D-022)."""
    if not demo_id.startswith("demo_") or demo_id.startswith("demo_dup_") or demo_id.startswith("demo_fault_"):
        return None
    # format: demo_{NNNN}_{resume_id}
    parts = demo_id.split("_", 2)
    if len(parts) != 3:
        return None
    return parts[2]


def ai_resume_id_from_demo_id(demo_id: str) -> Optional[str]:
    if not demo_id.startswith("shadow_"):
        return None
    return demo_id[len("shadow_") :]


def _normalize_step_value(action: str, evt: Optional[dict]) -> Optional[dict]:
    """Maps an action's raw event output/decision into a small canonical
    form for cross-source comparison. Returns None if evt is None.

    For a FAILED event, we compare the exception_type instead of the
    (trivially empty) output dict — two failures with empty output
    would otherwise register as a "data match" on no real evidence.
    Comparing exception_type is the actual meaningful signal: did both
    sides fail for the SAME reason?
    """
    if evt is None:
        return None
    if evt.get("result") == "failure":
        exc = evt.get("exception") or {}
        return {"failed": True, "exception_type": exc.get("exception_type")}

    output = evt.get("output") or {}
    decision = evt.get("decision")

    if action == "fetch_resume":
        return {"resume_id": output.get("resume_id")}
    if action == "extract_resume":
        return {
            "experience_years": output.get("experience_years"),
            "skills": sorted(output.get("skills") or []),
            "candidate_name": output.get("candidate_name"),
        }
    if action in ("check_experience", "compare_skills", "classify_candidate"):
        return {"outcome": decision["outcome"] if decision else None}
    if action == "update_candidate_record":
        status = output.get("status") or output.get("would_set_status")
        return {"status": status}
    if action == "send_interview_invitation":
        action_taken = output.get("status") == "sent" or output.get("would_send") is True
        return {"email_action_taken": bool(action_taken)}
    return dict(output)


DATA_STEPS = {"fetch_resume", "extract_resume"}
DECISION_STEPS = {"check_experience", "compare_skills", "classify_candidate"}


def _align_steps(human_events: list[dict], ai_events: list[dict]) -> list[dict]:
    """Aligns human and AI events for one resume by action name, and
    returns one comparison record per action that appears in EITHER
    trace (never silently drops an action present in only one side)."""
    human_by_action = {e["action"]: e for e in human_events}
    ai_by_action = {e["action"]: e for e in ai_events}
    all_actions_in_order = list(dict.fromkeys([e["action"] for e in human_events] + [e["action"] for e in ai_events]))

    records = []
    for action in all_actions_in_order:
        h_evt = human_by_action.get(action)
        a_evt = ai_by_action.get(action)
        h_val = _normalize_step_value(action, h_evt)
        a_val = _normalize_step_value(action, a_evt)

        note = ""
        if h_evt is None and a_evt is not None:
            # The known, documented asymmetry: AI always proposes a step for
            # send_interview_invitation even as a no-op; human demo doesn't
            # log the step at all when no action was ever attempted.
            if action == "send_interview_invitation" and a_val and a_val.get("email_action_taken") is False:
                note = (
                    "Human demo did not log this step (no_action by design, logger/human_demo.py only logs "
                    "an email event on shortlist). AI shadow always proposes a step, even a no-op. Both "
                    "represent 'no email sent' — treated as outcome-equivalent, not a mismatch."
                )
                match = True
            else:
                note = "AI reached a step the human trace never recorded — human may have stopped earlier (e.g. an exception)."
                match = False
        elif h_evt is not None and a_evt is None:
            note = "Human trace has a step the AI shadow run never reached — unexpected under the current workflow graph."
            match = False
        elif h_evt is not None and a_evt is not None:
            match = h_val == a_val
        else:
            match = None  # neither side has this action (shouldn't occur given all_actions_in_order construction)

        tool_agreement = None
        if h_evt is not None and a_evt is not None:
            tool_agreement = h_evt.get("application") == a_evt.get("application")

        records.append(
            {
                "action": action,
                "human_present": h_evt is not None,
                "ai_present": a_evt is not None,
                "human_value": h_val,
                "ai_value": a_val,
                "match": match,
                "tool_agreement": tool_agreement,
                "ai_confidence": a_evt.get("confidence") if a_evt else None,
                "human_result": h_evt.get("result") if h_evt else None,
                "ai_result": a_evt.get("result") if a_evt else None,
                "explanation": note or ("Match" if match else ("Mismatch" if match is False else "N/A")),
                "is_data_step": action in DATA_STEPS,
                "is_decision_step": action in DECISION_STEPS,
            }
        )
    return records


def compare_resume(resume_id: str, human_events: list[dict], ai_events: list[dict]) -> dict:
    """Section 13's per-case comparison: a full step-by-step table plus
    an overall outcome-agreement determination for this one resume."""
    step_records = _align_steps(human_events, ai_events)

    human_final_classification = next(
        (e["decision"]["outcome"] for e in human_events if e["action"] == "classify_candidate" and e.get("decision")),
        None,
    )
    ai_final_classification = next(
        (e["decision"]["outcome"] for e in ai_events if e["action"] == "classify_candidate" and e.get("decision")),
        None,
    )
    human_email_sent = any(
        e["action"] == "send_interview_invitation" and e.get("result") == "success" for e in human_events
    )
    ai_email_proposed = any(
        e["action"] == "send_interview_invitation" and (e.get("output") or {}).get("would_send") is True
        for e in ai_events
    )

    outcome_agreement = (human_final_classification == ai_final_classification) and (
        human_email_sent == ai_email_proposed
    )

    return {
        "resume_id": resume_id,
        "steps": step_records,
        "human_final_classification": human_final_classification,
        "ai_final_classification": ai_final_classification,
        "human_email_sent": human_email_sent,
        "ai_email_proposed": ai_email_proposed,
        "outcome_agreement": outcome_agreement,
    }


def compare_all(human_events: list[dict], ai_events: list[dict]) -> list[dict]:
    human_by_resume = _group_by_resume(human_events, human_resume_id_from_demo_id)
    ai_by_resume = _group_by_resume(ai_events, ai_resume_id_from_demo_id)

    all_resume_ids = sorted(set(human_by_resume) | set(ai_by_resume))
    return [
        compare_resume(resume_id, human_by_resume.get(resume_id, []), ai_by_resume.get(resume_id, []))
        for resume_id in all_resume_ids
    ]
