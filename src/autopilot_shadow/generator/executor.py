"""
Automation executor (Day 7, Section 11): proves the generated,
classified Workflow is actually executable — not just a diagram.

RESOLVES D-004: custom DAG runner, not LangGraph.

Why: this workflow is a short linear sequence with one optional tail
(Day 5's finding — no true multi-way branches exist in this data), and
the executor's main job for the rest of this project is precise,
auditable STEP-LEVEL CONTROL: stop exactly at a HUMAN_REVIEW/BLOCKED
step, hand off to an approval gate (Day 11), and later intercept every
tool call for shadow mode (Day 8) using the exact same EventLogger this
executor is built on. A custom ~80-line runner over our own Workflow
schema gives us that directly, with every stop/go decision visible in
our own code and tests. LangGraph would add a second graph abstraction
on top of the one we already built and validated in Days 5-7, with no
corresponding benefit for a workflow this shape — Section 34 explicitly
asks us to avoid unnecessary complexity and justify every tech choice.

HOW IT WORKS:
Walks the Workflow from entry_step_id, following `next_steps`. At each
step:
  - If step_type is AUTOMATE or AUTOMATE_WITH_MONITORING, it actually
    calls the step's handler (real mock-tool calls, logged as Events)
    and continues to the next step.
  - If step_type is HUMAN_REVIEW, HUMAN_ONLY, or BLOCKED, it logs a
    PENDING approval Event and STOPS — this project has no autonomous
    override of a human gate (Safety S3/S4). Day 11 builds the actual
    approve/edit/reject/escalate mechanism that resumes past this point;
    Day 7 only proves the stop happens at exactly the right place.
"""

from __future__ import annotations

from typing import Callable

from autopilot_shadow.logger.event_logger import EventLogger
from autopilot_shadow.mock_env.environment import MockEnvironment
from autopilot_shadow.schemas.event import ActorType, ApprovalState, DecisionRecord
from autopilot_shadow.schemas.workflow import StepType, Workflow

# A handler receives the running context, the environment, and the job
# description, and returns (output_dict, decision_or_None) — using the
# EventLogger's `decision_from_result` mode so the decision it computes
# (only known once the handler actually runs) is attached to the right Event.
ActionHandler = Callable[[dict, MockEnvironment, dict], tuple[dict, DecisionRecord | None]]

HALTING_STEP_TYPES = {StepType.HUMAN_REVIEW, StepType.HUMAN_ONLY, StepType.BLOCKED}


class AutomationExecutor:
    """Executes a classified Workflow against a MockEnvironment for one
    resume_id, respecting each step's automation classification."""

    def __init__(self, workflow: Workflow, handlers: dict[str, ActionHandler], actor: str = "automation_engine"):
        self.workflow = workflow
        self.handlers = handlers
        self.actor = actor

    def run(self, env: MockEnvironment, job_description: dict, resume_id: str, demo_id: str | None = None) -> EventLogger:
        logger = EventLogger(workflow_name=self.workflow.workflow_name, demo_id=demo_id)
        ctx: dict = {"resume_id": resume_id}

        step_id: str | None = self.workflow.entry_step_id
        while step_id is not None:
            step = self.workflow.get_step(step_id)

            if step.step_type in HALTING_STEP_TYPES:
                logger.log_action(
                    actor=self.actor,
                    actor_type=ActorType.AI_SHADOW,
                    application=step.application or "automation_engine",
                    action=step.action,
                    input_data={"step_type": step.step_type, "reason": step.classification_reason},
                    fn=lambda: {"status": "halted_pending_human_decision"},
                    approval=ApprovalState.PENDING,
                )
                break  # Day 7 does not resume past a human gate - that's Day 11

            handler = self.handlers.get(step.action)
            if handler is None:
                raise KeyError(f"No handler registered for action {step.action!r} (step {step.id})")

            evt = logger.log_action(
                actor=self.actor,
                actor_type=ActorType.AI_SHADOW,
                application=step.application or "automation_engine",
                action=step.action,
                input_data={"resume_id": resume_id},
                fn=lambda: handler(ctx, env, job_description),
                decision_from_result=True,
            )

            if evt.result == "failure":
                break  # mirrors human_demo's early-stop behavior on tool failure

            # Advance. Day 5's finding: this workflow has no true multi-way
            # branch, so taking the first next_step is correct here; a
            # future workflow with real branching would need the handler's
            # output to pick among next_steps explicitly.
            step_id = step.next_steps[0] if step.next_steps else None

        return logger
