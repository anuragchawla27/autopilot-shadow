"""
Human demonstration policy for the resume-screening workflow.

This module plays the role of "the human HR reviewer" so we can generate
realistic demonstration traces (Section 5 input) without a live person
sitting at a keyboard for 12 resumes. It implements the exact step
sequence from Section 5 of the brief:

    receive resume -> extract info -> check experience -> compare skills
    -> classify (shortlist / reject / human_review) -> update record
    -> send communication (only if shortlisted)

IMPORTANT — what this is and isn't:
- This is OUR OWN authored judgment policy, used only to generate
  synthetic demonstrations for a 15-day project with no real HR team
  available. It is documented here as our own design (see
  docs/03_established_vs_own_design.md), not claimed as a discovered or
  learned policy.
- The experience threshold rule (`experience < required -> reject`) is
  the EXPLICIT rule given verbatim in Section 8 of the brief.
- The skill-matching tiers below (full / partial / none / no-data) are
  our own inferred heuristic for producing varied, realistic outcomes
  across the synthetic resume set — Day 6's decision-extraction engine
  is what actually re-derives rules FROM these demonstrations; this
  policy is only the data-generation side, and must not be confused
  with that extraction step.
- A resume's `raw_text` is scanned only for a KNOWN, narrow prompt-
  injection pattern, as a stand-in for a vigilant human reviewer who
  ignores embedded instructions. This is a deliberate demonstration of
  Safety rule S5, not a general content filter.
"""

from __future__ import annotations

from autopilot_shadow.mock_env.environment import MockEnvironment
from autopilot_shadow.mock_env.faults import FaultType
from autopilot_shadow.schemas.event import ActorType, ApprovalState, DecisionRecord

from .event_logger import EventLogger

_INJECTION_MARKERS = ("ignore all previous instructions", "ignore previous instructions")


def _skill_match_tier(required_skills: set[str], candidate_skills: list[str]) -> str:
    if not candidate_skills:
        return "no_data"
    matched = required_skills & set(s.lower() for s in candidate_skills)
    if matched == required_skills:
        return "full"
    if matched:
        return "partial"
    return "none"


def _looks_like_prompt_injection(raw_text: str) -> bool:
    lowered = raw_text.lower()
    return any(marker in lowered for marker in _INJECTION_MARKERS)


def run_human_demo(
    env: MockEnvironment,
    job_description: dict,
    resume_id: str,
    actor: str = "hr_reviewer_1",
    fault_on_fetch: FaultType = FaultType.NONE,
    fault_on_parse: FaultType = FaultType.NONE,
    demo_id: str | None = None,
) -> EventLogger:
    """Runs one resume through the human workflow and returns the logger
    holding every Event produced. Stops early (like a real reviewer
    would) if fetch or parse fails."""

    logger = EventLogger(workflow_name="resume_screening", demo_id=demo_id)
    required_skills = set(s.lower() for s in job_description["required_skills"])
    required_experience = job_description["required_experience_years"]

    # Step 1: receive resume
    raw = logger.log_action(
        actor=actor,
        actor_type=ActorType.HUMAN,
        application="resume_db",
        action="fetch_resume",
        input_data={"resume_id": resume_id},
        fn=lambda: env.resume_db.fetch_resume(resume_id, fault=fault_on_fetch),
    )
    if raw.result == "failure":
        return logger  # can't proceed without the resume

    # Step 2: extract candidate information
    parsed_evt = logger.log_action(
        actor=actor,
        actor_type=ActorType.HUMAN,
        application="document_parser",
        action="extract_resume",
        input_data={"resume_id": resume_id},
        fn=lambda: env.document_parser.parse(_last_output_as_dict(env, resume_id), fault=fault_on_parse),
    )
    if parsed_evt.result == "failure":
        return logger  # can't proceed without parsed fields

    parsed = parsed_evt.output  # dict form of ParsedResume
    experience_years = float(parsed["experience_years"])
    skills = list(parsed["skills"])
    candidate_name = parsed["candidate_name"]

    # Step 3: check experience (EXPLICIT rule, Section 8)
    experience_ok = experience_years >= required_experience
    logger.log_action(
        actor=actor,
        actor_type=ActorType.HUMAN,
        application="document_parser",
        action="check_experience",
        input_data={"experience_years": experience_years, "required_experience": required_experience},
        fn=lambda: {"experience_ok": experience_ok},
        decision=DecisionRecord(
            decision_name="experience_check",
            outcome="sufficient" if experience_ok else "insufficient",
            evidence={"experience_years": experience_years, "required_experience": required_experience},
        ),
    )

    # Step 4: compare skills with JD
    tier = _skill_match_tier(required_skills, skills)
    logger.log_action(
        actor=actor,
        actor_type=ActorType.HUMAN,
        application="document_parser",
        action="compare_skills",
        input_data={"required_skills": sorted(required_skills), "candidate_skills": skills},
        fn=lambda: {"match_tier": tier},
        decision=DecisionRecord(
            decision_name="skill_comparison",
            outcome=tier,
            evidence={"required_skills": sorted(required_skills), "candidate_skills": skills},
        ),
    )

    # Step 5: eligibility assessment / classification
    injection_detected = _looks_like_prompt_injection(parsed["raw_text"])
    classification, reason = _classify(experience_ok, tier, injection_detected)

    logger.log_action(
        actor=actor,
        actor_type=ActorType.HUMAN,
        application="hr_policy",
        action="classify_candidate",
        input_data={"experience_ok": experience_ok, "skill_match_tier": tier, "injection_detected": injection_detected},
        fn=lambda: {"classification": classification},
        decision=DecisionRecord(decision_name="eligibility_assessment", outcome=classification, evidence={"reason": reason}),
        reasoning_summary=reason,
    )

    # Step 6: update candidate record
    logger.log_action(
        actor=actor,
        actor_type=ActorType.HUMAN,
        application="crm",
        action="update_candidate_record",
        input_data={"resume_id": resume_id, "status": classification},
        fn=lambda: env.crm.create_or_update_record(resume_id, candidate_name, status=classification, notes=reason),
    )

    # Step 7: communication decision — only on shortlist, and always with
    # explicit approval, matching Section 4's "requires explicit approval"
    if classification == "shortlist":
        email = parsed["email"]
        logger.log_action(
            actor=actor,
            actor_type=ActorType.HUMAN,
            application="email_service",
            action="send_interview_invitation",
            input_data={"to": email},
            fn=lambda: env.email_service.send_email(
                to=email, subject="Interview Invitation", body=f"Dear {candidate_name}, ...", approved=True
            ),
            approval=ApprovalState.APPROVED,
        )

    return logger


def _classify(experience_ok: bool, skill_tier: str, injection_detected: bool) -> tuple[str, str]:
    if injection_detected:
        return "human_review", "Resume text contains a suspected prompt-injection attempt; flagged for manual review regardless of extracted fields."
    if not experience_ok:
        return "reject", "Experience below required threshold (explicit rule)."
    if skill_tier == "full":
        return "shortlist", "Experience sufficient and all required skills present."
    if skill_tier == "partial":
        return "human_review", "Experience sufficient but only some required skills present."
    if skill_tier == "no_data":
        return "human_review", "No skill information could be extracted from the resume."
    # tier == "none": experience is fine but zero direct keyword matches —
    # could be a synonym/terminology mismatch rather than a true non-match.
    return "human_review", "Experience sufficient but no required skills matched by name; possible terminology mismatch (needs human judgment)."


def _last_output_as_dict(env: MockEnvironment, resume_id: str) -> dict:
    """fetch_resume returns the raw stored dict already; this helper exists
    only so log_action's `fn` can re-fetch consistently for the parse step
    without threading extra state through the logger."""
    return env.resume_db._store[resume_id]
