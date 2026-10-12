"""
Ablation Systems A and B's executors (Day 15, Section 31).

Both use the exact same `bare_decision.py` decision logic — the
ablation variable between them is purely architectural:

  System A (`BareNoStructureExecutor`): fetch, extract, check experience
  and classify collapse into ONE opaque call/Event — no per-step
  structure at all, the closest honest stand-in for "a single LLM call,
  no pipeline" this project can build without fabricating an LLM result
  (see `bare_decision.py`'s module docstring).

  System B (`BareStructuredExecutor`): the SAME bare decision, but now
  run through the real reconstructed Workflow (Day 5/7's step graph) —
  one Event per step, same as every other executor in this project.
  Nothing about the decision itself changes; only the architecture
  around it does. This isolates exactly what "+ workflow reconstruction"
  (Section 31's System B) contributes on its own: per-step traceability,
  not correctness — the two systems should reach the SAME classification
  per case, which the test suite checks directly.

Neither system has any approval gate — both walk straight through to
`send_interview_invitation` like Experiment B's `NaiveExecutor`, because
neither has the confidence or risk layer (Systems C/D) that would stop
them. This is deliberate: it isolates "does adding structure alone make
the system safer" (no) from "does adding confidence/risk make it safer"
(Systems C/D/E answer that).
"""

from __future__ import annotations

from autopilot_shadow.generator.handlers import ACTION_HANDLERS
from autopilot_shadow.logger.event_logger import EventLogger
from autopilot_shadow.mock_env.environment import MockEnvironment
from autopilot_shadow.schemas.event import ActorType
from autopilot_shadow.schemas.workflow import Workflow

from .bare_decision import bare_classify, bare_decide_everything

# Same handlers as every other executor for the mechanical steps
# (update_candidate_record, send_interview_invitation) — only
# classify_candidate's decision logic is swapped for the bare version.
_STRUCTURED_HANDLERS = dict(ACTION_HANDLERS)
_STRUCTURED_HANDLERS["classify_candidate"] = bare_classify


class BareNoStructureExecutor:
    """System A: one opaque decision call, then the two mechanical
    follow-on steps (record update, invitation draft) — no reconstructed
    workflow graph is consulted at all for the decision itself."""

    def __init__(self, actor: str = "ablation_system_a_bare_decision"):
        self.actor = actor

    def run(self, env: MockEnvironment, job_description: dict, resume_id: str, demo_id: str | None = None) -> EventLogger:
        logger = EventLogger(workflow_name="resume_screening", demo_id=demo_id)
        ctx: dict = {"resume_id": resume_id}

        # action="classify_candidate" (not a more descriptive name like
        # "decide_everything") deliberately: the shared outcome-extraction
        # helper (`engine._outcome_from_events`) identifies a case's final
        # decision by looking for THIS action name, same as every other
        # executor in this project. Naming it anything else would make
        # System A's decision invisible to that shared code (a real bug
        # caught while first building this: with a different action name,
        # `final_action` stayed None for every case, silently treating 10
        # ordinary sends as "unsafe" because None != "shortlist" — see
        # docs/18 for the full account). `input_data` records that this
        # one event actually did fetch+extract+check+classify combined.
        evt = logger.log_action(
            actor=self.actor,
            actor_type=ActorType.AI_SHADOW,
            application="ablation_system_a",
            action="classify_candidate",
            input_data={"resume_id": resume_id, "note": "combined fetch+extract+check+classify, one opaque call"},
            fn=lambda: bare_decide_everything(ctx, env, job_description),
            decision_from_result=True,
        )
        if evt.result == "failure":
            return logger

        for action in ("update_candidate_record", "send_interview_invitation"):
            handler = ACTION_HANDLERS[action]
            evt = logger.log_action(
                actor=self.actor,
                actor_type=ActorType.AI_SHADOW,
                application="ablation_system_a",
                action=action,
                input_data={"resume_id": resume_id},
                fn=lambda handler=handler: handler(ctx, env, job_description),
                decision_from_result=True,
            )
            if evt.result == "failure":
                break
        return logger


class BareStructuredExecutor:
    """System B: the same bare decision, now walked through the real
    reconstructed Workflow step by step — same shape as Experiment B's
    NaiveExecutor, with classify_candidate's handler swapped out."""

    def __init__(self, workflow: Workflow, actor: str = "ablation_system_b_structured"):
        self.workflow = workflow
        self.actor = actor

    def run(self, env: MockEnvironment, job_description: dict, resume_id: str, demo_id: str | None = None) -> EventLogger:
        logger = EventLogger(workflow_name=self.workflow.workflow_name, demo_id=demo_id)
        ctx: dict = {"resume_id": resume_id}

        step_id: str | None = self.workflow.entry_step_id
        while step_id is not None:
            step = self.workflow.get_step(step_id)
            handler = _STRUCTURED_HANDLERS.get(step.action)
            if handler is None:
                raise KeyError(f"No handler registered for action {step.action!r} (step {step.id})")

            evt = logger.log_action(
                actor=self.actor,
                actor_type=ActorType.AI_SHADOW,
                application=step.application or "ablation_system_b",
                action=step.action,
                input_data={"resume_id": resume_id, "step_type": step.step_type},
                fn=lambda handler=handler: handler(ctx, env, job_description),
                decision_from_result=True,
            )
            if evt.result == "failure":
                break
            step_id = step.next_steps[0] if step.next_steps else None

        return logger
