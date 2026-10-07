"""
Generic action handlers for the AutomationExecutor (Day 7).

Each handler has the signature (ctx, env, job_description) -> (output,
decision_or_None). They implement the SAME step logic as Day 4's
human_demo.py (fetch -> extract -> check experience -> compare skills ->
classify -> update record -> email), but driven generically by whatever
action name the Workflow graph visits next, rather than a hardcoded
sequence. This is what makes the reconstructed-and-classified Workflow
itself "a representation that can actually be executed" (Section 11),
instead of a diagram next to a separately hand-written script.

`send_interview_invitation` is included for completeness (and for Day 8
to reuse), but under current classification it is never reached by
AutomationExecutor — Section 22/criterion 1 always halts before it.
"""

from __future__ import annotations

from autopilot_shadow.common.feature_utils import looks_like_prompt_injection, skill_match_tier
from autopilot_shadow.mock_env.environment import MockEnvironment
from autopilot_shadow.schemas.event import DecisionRecord


def fetch_resume(ctx: dict, env: MockEnvironment, job_description: dict):
    raw = env.resume_db.fetch_resume(ctx["resume_id"])
    ctx["raw_resume"] = raw
    return raw, None


def extract_resume(ctx: dict, env: MockEnvironment, job_description: dict):
    parsed = env.document_parser.parse(ctx["raw_resume"])
    parsed_dict = {
        "resume_id": parsed.resume_id,
        "candidate_name": parsed.candidate_name,
        "email": parsed.email,
        "experience_years": parsed.experience_years,
        "skills": parsed.skills,
        "education": parsed.education,
        "raw_text": parsed.raw_text,
    }
    ctx["parsed"] = parsed_dict
    return parsed_dict, None


def check_experience(ctx: dict, env: MockEnvironment, job_description: dict):
    required = job_description["required_experience_years"]
    experience_years = ctx["parsed"]["experience_years"]
    experience_ok = experience_years >= required
    ctx["experience_ok"] = experience_ok
    decision = DecisionRecord(
        decision_name="experience_check",
        outcome="sufficient" if experience_ok else "insufficient",
        evidence={"experience_years": experience_years, "required_experience": required},
    )
    return {"experience_ok": experience_ok}, decision


def compare_skills(ctx: dict, env: MockEnvironment, job_description: dict):
    required_skills = set(s.lower() for s in job_description["required_skills"])
    skills = ctx["parsed"]["skills"]
    tier = skill_match_tier(required_skills, skills)
    ctx["skill_match_tier"] = tier
    decision = DecisionRecord(
        decision_name="skill_comparison",
        outcome=tier,
        evidence={"required_skills": sorted(required_skills), "candidate_skills": skills},
    )
    return {"match_tier": tier}, decision


def classify_candidate(ctx: dict, env: MockEnvironment, job_description: dict):
    injection_detected = looks_like_prompt_injection(ctx["parsed"]["raw_text"])
    experience_ok = ctx["experience_ok"]
    tier = ctx["skill_match_tier"]
    ctx["injection_detected"] = injection_detected  # stored for Day 8's confidence-matching context

    if injection_detected:
        classification, reason = "human_review", "Resume text contains a suspected prompt-injection attempt."
    elif not experience_ok:
        classification, reason = "reject", "Experience below required threshold (explicit rule)."
    elif tier == "full":
        classification, reason = "shortlist", "Experience sufficient and all required skills present."
    else:
        classification, reason = "human_review", f"Experience sufficient but skill match tier is {tier!r}."

    ctx["classification"] = classification
    decision = DecisionRecord(decision_name="eligibility_assessment", outcome=classification, evidence={"reason": reason})
    return {"classification": classification}, decision


def update_candidate_record(ctx: dict, env: MockEnvironment, job_description: dict):
    record = env.crm.create_or_update_record(
        ctx["resume_id"], ctx["parsed"]["candidate_name"], status=ctx["classification"], notes="Updated by automation_engine"
    )
    return {"status": record.status}, None


def send_interview_invitation(ctx: dict, env: MockEnvironment, job_description: dict):
    """Reachable only if classification somehow reached here with
    approval already granted — not possible via AutomationExecutor under
    current classification (criterion 1 halts first). Kept for Day 8 reuse."""
    draft = env.email_service.draft_email(
        to=ctx["parsed"]["email"], subject="Interview Invitation", body=f"Dear {ctx['parsed']['candidate_name']}, ..."
    )
    return draft, None


ACTION_HANDLERS = {
    "fetch_resume": fetch_resume,
    "extract_resume": extract_resume,
    "check_experience": check_experience,
    "compare_skills": compare_skills,
    "classify_candidate": classify_candidate,
    "update_candidate_record": update_candidate_record,
    "send_interview_invitation": send_interview_invitation,
}
