"""
The "bare decision" used by Ablation Systems A and B (Day 15, Section 31).

HONEST FRAMING (read this before anything else): Section 31 calls System
A "LLM automation only." This project never calls an LLM anywhere — no
API key, no model, nothing (D-009 is still open; every decision in this
codebase is deterministic rule-based Python). Simulating what a real LLM
call would have decided would mean inventing a result, which S7
forbids. Instead, Ablation A/B are reframed as the fair, honest
equivalent of what Section 31 is actually testing for: **a single opaque
decision function with no surrounding project architecture** — no
workflow reconstruction (Day 5), no labelled rule extraction (Day 6), no
confidence modeling (Day 8), no risk model (Day 10). An LLM call would
also be exactly this: one opaque decision, no architecture around it. The
ablation question Section 31 is really asking — "how much does each
layer of architecture actually contribute?" — is answered the same way
either way, because what's being measured is the SURROUNDING SYSTEM, not
which specific decision-maker sits at the center.

WHAT'S DELIBERATELY MISSING, compared to the real `classify_candidate`
in `generator/handlers.py`:
- No prompt-injection check (Day 7's `looks_like_prompt_injection`).
  This is the one piece of real decision logic withheld, and it produces
  a genuine, measured consequence (see `docs/18`): res_0012 is a
  deliberately adversarial resume (Section 17/S5's own test case) that
  meets every surface threshold (experience=2.0, all 3 required skills
  present) and should be routed to human_review — but only if something
  checks for the injection attempt first. A bare decision-maker with no
  such check gets this one wrong.
- No Day 6 rule lineage (`rule_type`/`rule_id`) attached to the outcome —
  there is nothing here for Day 8's confidence model to point at, which
  is the concrete reason Systems A/B cannot be confidence-aware at all,
  not just "aren't" by choice.

Everything else (the threshold logic itself: experience >= required AND
all required skills present -> shortlist) is intentionally UNCHANGED
from the real decision, because the ablation is about architecture, not
about making this baseline artificially worse than it has to be.
"""

from __future__ import annotations

from autopilot_shadow.common.feature_utils import skill_match_tier
from autopilot_shadow.mock_env.environment import MockEnvironment
from autopilot_shadow.schemas.event import DecisionRecord


def bare_classify(ctx: dict, env: MockEnvironment, job_description: dict):
    """The same threshold logic as `generator/handlers.py`'s
    `classify_candidate`, with NO prompt-injection check and NO rule
    lineage — see module docstring for why."""
    required_skills = set(s.lower() for s in job_description["required_skills"])
    tier = skill_match_tier(required_skills, ctx["parsed"]["skills"])
    ctx["skill_match_tier"] = tier

    if not ctx["experience_ok"]:
        classification, reason = "reject", "Experience below required threshold."
    elif tier == "full":
        classification, reason = "shortlist", "Experience sufficient and all required skills present."
    else:
        classification, reason = "human_review", f"Experience sufficient but skill match tier is {tier!r}."

    ctx["classification"] = classification
    decision = DecisionRecord(decision_name="eligibility_assessment", outcome=classification, evidence={"reason": reason})
    return {"classification": classification}, decision


def bare_decide_everything(ctx: dict, env: MockEnvironment, job_description: dict):
    """System A's single opaque step: fetch, extract, check experience and
    classify in ONE call with no intermediate Events — standing in for
    what a single LLM call with no surrounding pipeline would look like
    (one black-box decision, no per-step traceability)."""
    raw = env.resume_db.fetch_resume(ctx["resume_id"])
    ctx["raw_resume"] = raw
    parsed = env.document_parser.parse(raw)
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
    ctx["experience_ok"] = parsed.experience_years >= job_description["required_experience_years"]

    output, decision = bare_classify(ctx, env, job_description)
    return {"classification": output["classification"]}, decision
