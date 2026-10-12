"""
Experiment E's engine — "AI workflow + risk-aware automation": the
project's actual complete real-time decision logic (Days 7, 10, 11
combined into one walk), distinct from Experiment C.

WHY E DIFFERS FROM C, CONCRETELY: `AutomationExecutor` (Experiment C,
Day 7) halts by STEP — `classify_candidate`'s step_type is
`human_review` for every case alike (it's a step-level classification,
Section 9), so Experiment C halts there identically for all 12 resumes
regardless of how clear-cut any individual case actually is. This
executor instead scores EVERY step CASE BY CASE with Day 10's real risk
model (impact + this case's own confidence + historical agreement), so
a clean, high-confidence case can proceed further automatically than an
ambiguous one — the exact distinction Day 10/D-033 was built to make.
Any step whose Day 10 recommendation needs a gate (Day 11's
`GATE_REQUIRED_RECOMMENDATIONS`: `approval_required`, `human_review`,
`automate_with_monitoring`) halts for a human; only a clean `automate`
recommendation proceeds on its own — the same human-in-the-loop shape
Day 13's real readiness tier (`HUMAN_IN_THE_LOOP_READY`) already
describes, now walked step by step instead of summarized after the fact.
"""

from __future__ import annotations

from autopilot_shadow.exceptions.approval_gate import gate_for
from autopilot_shadow.generator.handlers import ACTION_HANDLERS
from autopilot_shadow.logger.event_logger import EventLogger
from autopilot_shadow.mock_env.environment import MockEnvironment
from autopilot_shadow.risk.risk_factors import ACTION_RISK_FACTORS
from autopilot_shadow.risk.risk_model import score_case
from autopilot_shadow.schemas.event import ActorType, ApprovalState
from autopilot_shadow.schemas.workflow import Workflow
from autopilot_shadow.shadow.confidence import confidence_for_decision_step, confidence_for_deterministic_step

CASE_SENSITIVE_CONFIDENCE_STEPS = {"classify_candidate"}

# Section 22's hard override (irreversible + external-facing) does not
# depend on confidence, outcome, or historical agreement at all — it is a
# property of the ACTION itself (risk_factors.py). A step like this must be
# gated BEFORE it runs, not after, or the "safe" executor would still
# commit the very action the override exists to stop. (Caught by testing:
# an earlier version of this executor scored every step AFTER running it,
# which meant send_interview_invitation's draft was already produced by
# the time the override fired — harmless here only because the real
# handler stops at draft_email, never send_email, but still the wrong
# order for an executor meant to demonstrate risk-aware gating.)
_HARD_OVERRIDE_ACTIONS = {
    action
    for action, factors in ACTION_RISK_FACTORS.items()
    if not factors.reversible and factors.external_facing
}


class RiskAwareExecutor:
    """Walks the classified Workflow for one resume, scoring each step
    with the real Day 10 risk model and halting whenever Day 11's gate
    logic says a human is needed — the project's actual complete
    decision chain, reused here rather than reimplemented."""

    def __init__(self, workflow: Workflow, historical_agreement: dict, actor: str = "risk_aware_engine"):
        self.workflow = workflow
        self.historical_agreement = historical_agreement
        self.actor = actor

    def run(self, env: MockEnvironment, job_description: dict, resume_id: str, demo_id: str | None = None) -> EventLogger:
        logger = EventLogger(workflow_name=self.workflow.workflow_name, demo_id=demo_id)
        ctx: dict = {"resume_id": resume_id}

        step_id: str | None = self.workflow.entry_step_id
        while step_id is not None:
            step = self.workflow.get_step(step_id)
            handler = ACTION_HANDLERS.get(step.action)
            if handler is None:
                raise KeyError(f"No handler registered for action {step.action!r} (step {step.id})")

            # Hard-override actions are gated BEFORE running, since their
            # risk does not depend on this case at all (see module docstring).
            if step.action in _HARD_OVERRIDE_ACTIONS:
                risk = score_case(
                    action=step.action,
                    resume_id=resume_id,
                    confidence=1.0,  # irrelevant to this override, but score_case requires a value
                    result="success",
                    historical_agreement_rate=self.historical_agreement.get(step.action, {}).get("rate"),
                )
                logger.log_action(
                    actor=self.actor,
                    actor_type=ActorType.AI_SHADOW,
                    application=step.application or "risk_aware_engine",
                    action=f"{step.action}_gate",
                    input_data={"resume_id": resume_id, "risk_score": risk.risk_score, "recommendation": risk.recommendation},
                    fn=lambda: {"status": "halted_pending_human_decision", "reason": risk.reason},
                    approval=ApprovalState.PENDING,
                )
                break

            # Run the step for real first (we need its actual confidence and
            # result to score it honestly) — mirrors the shadow engine's own
            # "run, then score" order, not "guess, then maybe run."
            evt = logger.log_action(
                actor=self.actor,
                actor_type=ActorType.AI_SHADOW,
                application=step.application or "risk_aware_engine",
                action=step.action,
                input_data={"resume_id": resume_id},
                fn=lambda handler=handler: handler(ctx, env, job_description),
                decision_from_result=True,
            )

            if evt.result == "failure":
                break

            if step.action in CASE_SENSITIVE_CONFIDENCE_STEPS and step.rules:
                case_context = {
                    "experience_years": ctx["parsed"]["experience_years"],
                    "required_skills_present": ctx.get("skill_match_tier") == "full",
                    "experience_ok": ctx.get("experience_ok"),
                    "skill_match_tier": ctx.get("skill_match_tier"),
                    "injection_detected": ctx.get("injection_detected"),
                }
                actual_outcome = evt.decision.outcome if evt.decision else ""
                confidence, _ = confidence_for_decision_step(step, case_context, actual_outcome)
            else:
                confidence, _ = confidence_for_deterministic_step()

            hist = self.historical_agreement.get(step.action, {}).get("rate")
            risk = score_case(
                action=step.action,
                resume_id=resume_id,
                confidence=confidence,
                result=evt.result,
                historical_agreement_rate=hist,
            )
            gate = gate_for(risk.as_dict())

            if gate.gate_required:
                logger.log_action(
                    actor=self.actor,
                    actor_type=ActorType.AI_SHADOW,
                    application=step.application or "risk_aware_engine",
                    action=f"{step.action}_gate",
                    input_data={"resume_id": resume_id, "risk_score": risk.risk_score, "recommendation": risk.recommendation},
                    fn=lambda: {"status": "halted_pending_human_decision", "reason": risk.reason},
                    approval=ApprovalState.PENDING,
                )
                break

            step_id = step.next_steps[0] if step.next_steps else None

        return logger
