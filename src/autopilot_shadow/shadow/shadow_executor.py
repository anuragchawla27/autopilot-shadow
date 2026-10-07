"""
Shadow execution engine (Day 8, Section 12 — the brief's central feature).

Unlike Day 7's AutomationExecutor (which HALTS at a HUMAN_REVIEW/BLOCKED
step because it's deciding what to actually execute), the ShadowExecutor
runs EVERY step of the workflow for every case, because its only job is
to record what the AI WOULD have done — it never commits a real action,
so there's nothing it needs to stop and wait for a human about.

Section 12, implemented directly:
  "AI WORKFLOW: At the same time, the AI generates what it would have
   done, but does not perform irreversible external actions. Instead it
   records: proposed action, selected tool, extracted information,
   decision, confidence, and expected result."

DESIGN DECISIONS (see docs/10 and the decision log):

1. Shadow runs use their OWN fresh MockEnvironment, never the human
   demo's. Two reasons: (a) it mirrors reality — the AI and the human
   are independent observers of the same resume, not one acting on the
   other's already-mutated state; (b) it avoids a real bug we caught
   while designing this: re-fetching a resume the human already fetched
   would otherwise trip our own duplicate-submission detector
   (resume_db.py), which is a false positive for two separate observers
   reading the same document, not an actual duplicate request.

2. Every step actually RUNS (real computation against the shadow's own
   environment) so confidence and decisions are grounded in real
   extracted data — but steps that would mutate shared state in the real
   handlers (update_candidate_record, send_interview_invitation) are
   swapped for the shadow-safe versions in shadow_handlers.py, which
   compute and RECORD a proposal without committing it. This is a
   stronger safety boundary than "only block irreversible actions" —
   NOTHING is actually written to any tool in shadow mode, reversible or
   not, because mixing a real AI write into the human's own record would
   corrupt the very comparison Day 9 needs to make.

3. actor_type=AI_SHADOW and approval=NOT_REQUIRED on every shadow Event
   (there's nothing to approve yet — these are proposals, not automation
   requests; Day 11 builds the approval flow for ACTUAL automation).
"""

from __future__ import annotations

from autopilot_shadow.logger.event_logger import EventLogger
from autopilot_shadow.mock_env.environment import MockEnvironment
from autopilot_shadow.schemas.event import ActorType
from autopilot_shadow.schemas.workflow import Workflow

from .confidence import confidence_for_decision_step, confidence_for_deterministic_step
from .shadow_handlers import SHADOW_ACTION_HANDLERS

# Steps whose confidence depends on THIS case's specific evidence (which
# Day 6 rule matches it) rather than being fixed for the step overall.
CASE_SENSITIVE_CONFIDENCE_STEPS = {"classify_candidate"}


class ShadowExecutor:
    """Runs the full classified Workflow against a FRESH MockEnvironment
    for one resume, producing AI-proposed Events for every step —
    whether or not that step would halt under AutomationExecutor."""

    def __init__(self, workflow: Workflow, actor: str = "ai_shadow_engine"):
        self.workflow = workflow
        self.actor = actor

    def run(self, resumes: list[dict], job_description: dict, resume_id: str, demo_id: str | None = None) -> EventLogger:
        # Decision 1 (see module docstring): a fresh environment, never
        # the human demo's.
        shadow_env = MockEnvironment(resumes)

        logger = EventLogger(workflow_name=self.workflow.workflow_name, demo_id=demo_id)
        ctx: dict = {"resume_id": resume_id}

        step_id: str | None = self.workflow.entry_step_id
        while step_id is not None:
            step = self.workflow.get_step(step_id)
            handler = SHADOW_ACTION_HANDLERS.get(step.action)
            if handler is None:
                raise KeyError(f"No shadow handler registered for action {step.action!r} (step {step.id})")

            if step.action in CASE_SENSITIVE_CONFIDENCE_STEPS:

                def _call_with_case_confidence(handler=handler, step=step):
                    output, decision = handler(ctx, shadow_env, job_description)
                    case_context = {
                        "experience_years": ctx["parsed"]["experience_years"],
                        "required_skills_present": ctx.get("skill_match_tier") == "full",
                        "experience_ok": ctx.get("experience_ok"),
                        "skill_match_tier": ctx.get("skill_match_tier"),
                        "injection_detected": ctx.get("injection_detected"),
                    }
                    confidence, explanation = confidence_for_decision_step(step, case_context, decision.outcome)
                    return output, decision, confidence, explanation

                evt = logger.log_action(
                    actor=self.actor,
                    actor_type=ActorType.AI_SHADOW,
                    application=step.application or "ai_shadow_engine",
                    action=step.action,
                    input_data={"resume_id": resume_id, "step_type": step.step_type},
                    fn=_call_with_case_confidence,
                    confidence_from_result=True,
                )
            else:
                conf, explanation = confidence_for_deterministic_step()
                evt = logger.log_action(
                    actor=self.actor,
                    actor_type=ActorType.AI_SHADOW,
                    application=step.application or "ai_shadow_engine",
                    action=step.action,
                    input_data={"resume_id": resume_id, "step_type": step.step_type},
                    fn=lambda handler=handler: handler(ctx, shadow_env, job_description),
                    decision_from_result=True,
                    confidence=conf,
                    reasoning_summary=explanation,
                )

            if evt.result == "failure":
                break

            step_id = step.next_steps[0] if step.next_steps else None

        return logger
