"""
Experiment D's engine — "AI workflow + confidence threshold" (Section
21), gating purely on confidence, with NO risk model and NO hard
safety override yet (those are Experiment E / Day 10's job).

Section 21's own illustrative thresholds:
  confidence > 90%   -> automate
  70-90%             -> monitor (execute, flagged) or review depending on risk
  < 70%               -> human review

Since this experiment deliberately has no risk signal available yet
(that's what Experiment E adds), the 70-90% band always resolves to
"monitor and execute" here rather than "review" — the more permissive
reading, which is also the more honest one for what this experiment is
meant to show: confidence alone, without Section 22's hard override,
is not sufficient to catch an irreversible+external action just
because its confidence happens to be high.

WHY THIS MATTERS (the actual point of Experiment D): every
"deterministic" step (fetch/extract/check/compare/update/send, per
`shadow/confidence.py`) carries a FIXED 0.99 confidence — it describes
how much judgment the computation involves, not whether the action is
safe to take alone. Gating on confidence alone therefore auto-executes
`send_interview_invitation` for every case that reaches it, the same
as the naive baseline (Experiment B) — demonstrating concretely why
Day 10's risk model and its hard override (Section 22) exist: they are
what actually stops a high-confidence irreversible action, not
confidence by itself.
"""

from __future__ import annotations

from autopilot_shadow.generator.handlers import ACTION_HANDLERS
from autopilot_shadow.logger.event_logger import EventLogger
from autopilot_shadow.mock_env.environment import MockEnvironment
from autopilot_shadow.schemas.event import ActorType, ApprovalState
from autopilot_shadow.schemas.workflow import Workflow
from autopilot_shadow.shadow.confidence import confidence_for_decision_step, confidence_for_deterministic_step

AUTOMATE_THRESHOLD = 0.90
REVIEW_THRESHOLD = 0.70
CASE_SENSITIVE_CONFIDENCE_STEPS = {"classify_candidate"}


class ConfidenceOnlyExecutor:
    """Walks the classified Workflow for one resume, halting only when a
    step's OWN confidence falls below Section 21's review threshold —
    no risk factors, no hard override."""

    def __init__(self, workflow: Workflow, actor: str = "confidence_only_engine"):
        self.workflow = workflow
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

            # Peek at this case's confidence BEFORE deciding whether to run the
            # step for real, for judgment steps where that's knowable in
            # advance from already-collected context (classify_candidate is
            # the only one — its rules need experience_ok/skill_match_tier/
            # injection_detected, all already in ctx by the time we reach it).
            if step.action in CASE_SENSITIVE_CONFIDENCE_STEPS and step.rules:
                case_context = {
                    "experience_years": ctx["parsed"]["experience_years"],
                    "required_skills_present": ctx.get("skill_match_tier") == "full",
                    "experience_ok": ctx.get("experience_ok"),
                    "skill_match_tier": ctx.get("skill_match_tier"),
                    "injection_detected": ctx.get("injection_detected"),
                }
                # We don't know the outcome yet without running the handler,
                # so estimate confidence by the best matching rule regardless
                # of outcome — a provisional pre-check, exactly the kind of
                # shortcut a confidence-only gate is prone to.
                from autopilot_shadow.common.rule_evaluation import rule_matches

                matching = [r for r in step.rules if rule_matches(r, case_context)]
                if matching:
                    best = min(matching, key=lambda r: ["explicit", "inferred", "unknown"].index(r.rule_type))
                    conf_estimate = {"explicit": 0.95, "inferred": 0.75, "unknown": 0.40}[best.rule_type]
                else:
                    conf_estimate = 0.30

                if conf_estimate < REVIEW_THRESHOLD:
                    logger.log_action(
                        actor=self.actor,
                        actor_type=ActorType.AI_SHADOW,
                        application=step.application or "confidence_only_engine",
                        action=step.action,
                        input_data={"resume_id": resume_id, "confidence_estimate": conf_estimate},
                        fn=lambda: {"status": "halted_low_confidence"},
                        approval=ApprovalState.PENDING,
                    )
                    break

            evt = logger.log_action(
                actor=self.actor,
                actor_type=ActorType.AI_SHADOW,
                application=step.application or "confidence_only_engine",
                action=step.action,
                input_data={"resume_id": resume_id},
                fn=lambda handler=handler: handler(ctx, env, job_description),
                decision_from_result=True,
            )

            if evt.result == "failure":
                break

            step_id = step.next_steps[0] if step.next_steps else None

        return logger
