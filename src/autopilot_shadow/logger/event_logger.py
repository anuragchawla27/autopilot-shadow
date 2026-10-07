"""
Event logger — wraps calls into the mock environment (Day 3) and turns
each one into a Day 2 `Event`. This is the ONLY place in the codebase
that constructs Events from live tool calls, so every downstream
component (reconstruction, decision extraction, comparison) sees data
in exactly one shape, regardless of who called what.

Design choice: the logger does not decide what to do — it only records
what happened. The decision of WHICH action to take next belongs to the
"human demo policy" (this file, `HumanDemoPolicy`) for Day 4's synthetic
demonstrations, and later to the AI shadow engine (Day 8). Keeping
"decide" and "record" separate means the exact same logger will wrap the
AI's actions in shadow mode without any changes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from autopilot_shadow.mock_env.environment import MockEnvironment
from autopilot_shadow.mock_env.faults import FaultType, MockToolError
from autopilot_shadow.mock_env.resume_db import DuplicateResumeAlreadyFetched
from autopilot_shadow.schemas.event import (
    ActorType,
    ApprovalState,
    DecisionRecord,
    Event,
    ExceptionRecord,
    ExceptionType,
)

_FAULT_TO_EXCEPTION_TYPE = {
    FaultType.TOOL_FAILURE: ExceptionType.TOOL_FAILURE,
    FaultType.MALFORMED_INPUT: ExceptionType.UNEXPECTED_FORMAT,
    FaultType.MISSING_INFORMATION: ExceptionType.MISSING_DOCUMENT,
    FaultType.API_TIMEOUT: ExceptionType.API_UNAVAILABLE,
    FaultType.DUPLICATE_REQUEST: ExceptionType.DUPLICATE_RECORD,
}


class EventLogger:
    """Records one Event per logical action taken by an actor (human or AI)
    against the mock environment, in order, for a single demo run.
    """

    def __init__(self, workflow_name: str, demo_id: Optional[str] = None):
        self.workflow_name = workflow_name
        self.demo_id = demo_id or f"demo_{uuid.uuid4().hex[:8]}"
        self._step_index = 0
        self._clock = datetime(2026, 9, 1, 9, 0, 0)  # deterministic synthetic clock
        self.events: list[Event] = []

    def _next_timestamp(self) -> datetime:
        self._clock += timedelta(seconds=5)
        return self._clock

    def log_action(
        self,
        actor: str,
        actor_type: ActorType,
        application: str,
        action: str,
        fn: Callable[[], Any],
        input_data: Optional[dict] = None,
        decision: Optional[DecisionRecord] = None,
        reasoning_summary: Optional[str] = None,
        approval: ApprovalState = ApprovalState.NOT_REQUIRED,
        confidence: Optional[float] = None,
        decision_from_result: bool = False,
        confidence_from_result: bool = False,
    ) -> Event:
        """Runs `fn()` (a call into the mock environment), then records the
        outcome as an Event — success, or a caught MockToolError / duplicate
        turned into a structured ExceptionRecord. Never raises past this
        point: a failed action is a valid, loggable outcome, not a crash.

        `decision_from_result=True` (added Day 7, for the automation
        executor): `fn()` is expected to return `(output, decision)`
        instead of just `output`. This lets a handler compute its own
        DecisionRecord from data only available once it actually runs,
        without the caller having to know the decision before calling
        `fn()` — the chicken-and-egg problem a naive closure would hit.
        Day 4's calls never pass this flag, so existing behavior is
        unchanged.

        `confidence_from_result=True` (added Day 8, for the shadow
        executor): `fn()` additionally returns a (confidence,
        reasoning_summary) pair appended to the tuple — i.e.
        `(output, decision, confidence, reasoning_summary)` — because
        shadow-mode confidence depends on which Day 6 rule matches THIS
        case's evidence, known only once the handler runs. Requires
        decision_from_result=True. Any `confidence`/`reasoning_summary`
        passed directly to this call are overridden by the result in
        that case.
        """
        event_id = f"evt_{uuid.uuid4().hex[:8]}"
        input_data = input_data or {}

        try:
            raw_result = fn()
            if confidence_from_result:
                result, decision, confidence, reasoning_summary = raw_result
            elif decision_from_result:
                result, decision = raw_result
            else:
                result = raw_result
            evt = Event(
                event_id=event_id,
                demo_id=self.demo_id,
                workflow_name=self.workflow_name,
                step_index=self._step_index,
                timestamp=self._next_timestamp(),
                actor=actor,
                actor_type=actor_type,
                application=application,
                action=action,
                input=input_data,
                output=_to_output_dict(result),
                decision=decision,
                reasoning_summary=reasoning_summary,
                result="success",
                exception=None,
                approval=approval,
                confidence=confidence,
            )
        except (MockToolError, DuplicateResumeAlreadyFetched, KeyError, PermissionError) as exc:
            exc_record = _exception_from_error(exc)
            evt = Event(
                event_id=event_id,
                demo_id=self.demo_id,
                workflow_name=self.workflow_name,
                step_index=self._step_index,
                timestamp=self._next_timestamp(),
                actor=actor,
                actor_type=actor_type,
                application=application,
                action=action,
                input=input_data,
                output={},
                decision=decision,
                reasoning_summary=reasoning_summary,
                result="failure",
                exception=exc_record,
                approval=approval,
                confidence=confidence,
            )

        self._step_index += 1
        self.events.append(evt)
        return evt


def _to_output_dict(result: Any) -> dict:
    """Best-effort conversion of a mock-tool return value into a plain dict
    for storage on the Event, since dataclasses aren't directly JSON-able."""
    if result is None:
        return {}
    if isinstance(result, dict):
        return result
    if hasattr(result, "__dict__"):
        return {k: v for k, v in vars(result).items() if not k.startswith("_")}
    return {"value": result}


def _exception_from_error(exc: Exception) -> ExceptionRecord:
    if isinstance(exc, MockToolError):
        return ExceptionRecord(
            exception_type=_FAULT_TO_EXCEPTION_TYPE.get(exc.fault_type, ExceptionType.OTHER),
            description=str(exc),
            recovered=False,
        )
    if isinstance(exc, DuplicateResumeAlreadyFetched):
        return ExceptionRecord(exception_type=ExceptionType.DUPLICATE_RECORD, description=str(exc), recovered=False)
    if isinstance(exc, KeyError):
        return ExceptionRecord(exception_type=ExceptionType.MISSING_DOCUMENT, description=str(exc), recovered=False)
    if isinstance(exc, PermissionError):
        return ExceptionRecord(exception_type=ExceptionType.OTHER, description=str(exc), recovered=False)
    return ExceptionRecord(exception_type=ExceptionType.OTHER, description=str(exc), recovered=False)
