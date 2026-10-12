"""
Experiment B's engine — "AI-generated workflow," run with NO safety
gates at all: every step executes regardless of its Day 7 classification.

THIS IS DELIBERATELY THE UNSAFE BASELINE. Section 1 of the brief opens
with exactly this scenario: "If an AI system automatically executes
every step, a small misunderstanding can result in... unwanted
messages... irreversible business actions." Experiment B exists to
MEASURE that risk concretely against this project's own data, not just
assert it — everything else this project built (Day 7's classification
halting, Day 10's risk model, Day 11's approval gates) exists because
of what this experiment is expected to show.

HOW IT DIFFERS FROM `generator/executor.py`'s `AutomationExecutor`:
`AutomationExecutor` stops at a HUMAN_REVIEW/HUMAN_ONLY/BLOCKED step
(Day 7, Section 9). `NaiveExecutor` below does not look at step_type at
all — it walks the same step graph and just keeps calling handlers.

SAFETY NOTE: `generator/handlers.py`'s `send_interview_invitation`
still only ever calls `email_service.draft_email` (never `send_email`)
— that safety boundary lives in the mock tool/handler layer, not in
this orchestrator, so even this deliberately-unsafe experiment cannot
actually send a real email (S2/S3 hold regardless of orchestration).
What it CAN do, and is expected to, is draft an interview invitation
for a candidate who should have been rejected or sent to human review
— a concrete, measurable instance of exactly the failure Section 1
warns about.
"""

from __future__ import annotations

from autopilot_shadow.generator.handlers import ACTION_HANDLERS
from autopilot_shadow.logger.event_logger import EventLogger
from autopilot_shadow.mock_env.environment import MockEnvironment
from autopilot_shadow.schemas.event import ActorType
from autopilot_shadow.schemas.workflow import Workflow


class NaiveExecutor:
    """Walks the full classified Workflow for one resume, calling every
    step's real handler, with no step-type check and no approval gate.
    Deliberately unsafe — see module docstring."""

    def __init__(self, workflow: Workflow, actor: str = "naive_full_auto_engine"):
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

            evt = logger.log_action(
                actor=self.actor,
                actor_type=ActorType.AI_SHADOW,
                application=step.application or "naive_full_auto_engine",
                action=step.action,
                input_data={"resume_id": resume_id, "step_type": step.step_type},
                fn=lambda handler=handler: handler(ctx, env, job_description),
                decision_from_result=True,
            )

            if evt.result == "failure":
                break

            step_id = step.next_steps[0] if step.next_steps else None

        return logger
