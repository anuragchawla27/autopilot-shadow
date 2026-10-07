"""
Shadow-safe action handlers (Day 8).

Reuses Day 7's generator/handlers.py logic for every READ-ONLY /
computation step (fetch, extract, check_experience, compare_skills,
classify_candidate) unchanged — those have no side effect worth
distinguishing in shadow mode. For the two steps that mutate state in
the real handlers (update_candidate_record, send_interview_invitation),
this module provides SHADOW-SAFE versions that compute and RECORD what
would happen without calling the real mutating mock-tool methods.

CRITICAL SAFETY GUARANTEE: `shadow_send_interview_invitation` calls
ONLY `env.email_service.draft_email` (never `send_email`). There is no
code path in this module that can reach `send_email`. This is checked
structurally by a test (parses this file's source for the string
"send_email(" and fails if found standalone), not just promised in a
comment.
"""

from __future__ import annotations

from autopilot_shadow.mock_env.environment import MockEnvironment
from autopilot_shadow.schemas.event import DecisionRecord

from ..generator.handlers import (
    check_experience,
    classify_candidate,
    compare_skills,
    extract_resume,
    fetch_resume,
)


def shadow_update_candidate_record(ctx: dict, env: MockEnvironment, job_description: dict):
    """Does NOT call env.crm.create_or_update_record — that would commit
    a real write. Records what the AI would have written instead."""
    proposed = {
        "would_update_resume_id": ctx["resume_id"],
        "would_set_status": ctx["classification"],
        "note": "SHADOW MODE: no real CRM write performed.",
    }
    return proposed, None


def shadow_send_interview_invitation(ctx: dict, env: MockEnvironment, job_description: dict):
    """Only ever calls draft_email (no side effect, never sends). Never
    calls send_email — see module docstring for the safety guarantee.

    BUG CAUGHT WHILE TESTING Day 8: the first version of this handler
    drafted an interview invitation unconditionally, regardless of the
    classification this same case received at classify_candidate — so a
    REJECTED candidate still got an "AI would send an interview invite"
    proposal, which is wrong and would have poisoned Day 9's comparison
    (a disagreement that isn't really about communication, but about an
    upstream step this handler shouldn't re-decide). Fixed: this handler
    now checks ctx["classification"] and proposes "no action" for
    anything other than "shortlist" — mirroring Section 4's own
    "Communication decision" being conditional on a shortlist outcome.
    """
    if ctx.get("classification") != "shortlist":
        return (
            {
                "would_send": False,
                "note": f"SHADOW MODE: no email proposed — classification was "
                f"{ctx.get('classification')!r}, not 'shortlist'.",
            },
            None,
        )

    draft = env.email_service.draft_email(
        to=ctx["parsed"]["email"],
        subject="Interview Invitation",
        body=f"Dear {ctx['parsed']['candidate_name']}, ...",
    )
    draft["would_send"] = True
    draft["note"] = "SHADOW MODE: drafted only, never sent."
    return draft, None


SHADOW_ACTION_HANDLERS = {
    "fetch_resume": fetch_resume,
    "extract_resume": extract_resume,
    "check_experience": check_experience,
    "compare_skills": compare_skills,
    "classify_candidate": classify_candidate,
    "update_candidate_record": shadow_update_candidate_record,
    "send_interview_invitation": shadow_send_interview_invitation,
}
