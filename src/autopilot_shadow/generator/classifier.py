"""
Automation candidate classifier (Day 7, Section 9).

Section 9 is explicit: "The classification must be based on explicit
criteria. Do not simply assign labels arbitrarily." This module is that
set of criteria, applied in a fixed order, each with a written reason
attached to the step it produces (`classification_reason` is NEVER left
blank — enforced by a test).

CRITERIA, APPLIED IN ORDER (our own design — see docs/03):

  1. IRREVERSIBLE + EXTERNAL-FACING  -> HUMAN_REVIEW
     Matches Section 22's hard safety rule: an irreversible action that
     reaches outside our systems always needs explicit human approval,
     regardless of how well-evidenced the decision behind it is.

  2. NO RULES, BUT THE ACTION IS A NOISY/AMBIGUOUS COMPUTATION
     (`MONITORED_COMPUTATION_ACTIONS`) -> AUTOMATE_WITH_MONITORING
     Section 4's own table says this explicitly: "Skill matching:
     Automatable with confidence monitoring" — distinct from "Experience
     calculation: Potentially automatable" (plain). We also directly
     OBSERVED why: res_0004 in Day 4/6's data is a skill-matching
     ambiguity (synonyms, not exact terms) that this exact step gets
     wrong by keyword-matching alone. This criterion is deliberately
     evidence-aware, not just copied from the brief's table.

  3. NO RULES, EVERYTHING ELSE (pure fetch/extract/numeric check)
     -> AUTOMATE
     Nothing here involves judgment — it's a deterministic lookup or
     computation with no business decision in it.

  4. HAS RULES, AND EVERY RULE ATTACHED IS EXPLICIT (evidence-backed by
     stated config, Day 6) -> AUTOMATE_WITH_MONITORING
     Well-grounded, but still drives a business outcome, so it's
     monitored rather than left fully unsupervised.

  5. HAS A MIX OF EXPLICIT AND NON-EXPLICIT (inferred/unknown) RULES
     -> HUMAN_REVIEW
     Some paths through this step are well understood; others are not.
     The AI can prepare a recommendation, but a human finalizes it —
     exactly Section 4's own worked example ("Ambiguous candidate
     assessment: Human review may be required").

  6. EVERY RULE ATTACHED IS UNKNOWN (zero explicit/inferred support)
     -> BLOCKED
     Insufficient information to automate at any level yet.

NOTE ON PROPAGATION: `update_candidate_record` has no rules of its own
and is not a noisy computation, so it gets AUTOMATE under criterion 3 —
it does NOT inherit `classify_candidate`'s HUMAN_REVIEW uncertainty.
This is intentional, not an oversight: by the time this step runs, the
candidate's status has already been through classify_candidate's own
gate (automatically if well-evidenced, or via human approval once Day
11 builds that gate). Recording an already-resolved status is a
separate, low-risk, independently-automatable action — it is not
re-deciding anything.
"""

from __future__ import annotations

from autopilot_shadow.schemas.workflow import RiskLevel, RuleType, StepType, Workflow, WorkflowStep

from .risk_profile import RISK_PROFILE

# Section 4's table singles out skill matching as needing monitoring even
# though it's a pure computation step with no attached decision rule —
# and Day 4/6's own data (res_0004) shows exactly why: keyword-based skill
# matching misses synonyms. check_experience is plain numeric comparison
# with no such ambiguity, so it is NOT in this set.
MONITORED_COMPUTATION_ACTIONS = {"compare_skills"}


def classify_step(step: WorkflowStep) -> tuple[StepType, RiskLevel, str]:
    tag = RISK_PROFILE.get(step.action)
    risk = RiskLevel(tag.risk) if tag else RiskLevel.UNKNOWN

    # Criterion 1
    if tag and not tag.reversible and tag.external_facing:
        return (
            StepType.HUMAN_REVIEW,
            risk,
            f"Criterion 1: irreversible + external-facing ({tag.justification}) — "
            f"Section 22 requires explicit human approval regardless of rule evidence.",
        )

    # Criterion 2
    if not step.rules and step.action in MONITORED_COMPUTATION_ACTIONS:
        return (
            StepType.AUTOMATE_WITH_MONITORING,
            risk,
            "Criterion 2: no decision rules attached, but this action is a noisy/ambiguous "
            "computation (Section 4: 'Skill matching: Automatable with confidence monitoring'); "
            "Day 4/6's own data (res_0004) shows keyword-based skill matching misses synonyms.",
        )

    # Criterion 3
    if not step.rules:
        return (
            StepType.AUTOMATE,
            risk,
            "Criterion 3: no decision rules attached to this step — it is a deterministic "
            "lookup/computation with no business judgment involved.",
        )

    rule_types = {r.rule_type for r in step.rules}

    # Criterion 4
    if rule_types == {RuleType.EXPLICIT}:
        return (
            StepType.AUTOMATE_WITH_MONITORING,
            risk,
            f"Criterion 4: all {len(step.rules)} attached rule(s) are EXPLICIT "
            f"(backed by stated JD configuration) — well-grounded, but still drives "
            f"a business outcome, so monitored rather than unsupervised.",
        )

    # Criterion 6
    if rule_types == {RuleType.UNKNOWN}:
        return (
            StepType.BLOCKED,
            risk,
            f"Criterion 6: all {len(step.rules)} attached rule(s) are UNKNOWN "
            f"(insufficient evidence) — not enough information to automate at any level.",
        )

    # Criterion 5 (mix of explicit and non-explicit, or inferred present)
    explicit_count = sum(1 for r in step.rules if r.rule_type == RuleType.EXPLICIT)
    non_explicit_count = len(step.rules) - explicit_count
    return (
        StepType.HUMAN_REVIEW,
        risk,
        f"Criterion 5: mixed rule evidence ({explicit_count} explicit, {non_explicit_count} "
        f"inferred/unknown) — some decision paths are well understood, others are not. "
        f"AI may prepare a recommendation; a human finalizes it.",
    )


def classify_workflow(workflow: Workflow) -> Workflow:
    """Mutates and returns `workflow` with step_type, risk and
    classification_reason filled in on every step, using classify_step's
    explicit criteria. Never leaves a step UNCLASSIFIED / UNKNOWN risk /
    with no reason — enforced by tests."""
    for step in workflow.steps:
        step_type, risk, reason = classify_step(step)
        step.step_type = step_type
        step.risk = risk
        step.classification_reason = reason
    return workflow
