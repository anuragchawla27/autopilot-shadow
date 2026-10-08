"""
Exception detection (Day 11, Section 17).

Section 17's rule is explicit and small:

    IF confidence < threshold
    OR required_data_missing
    OR conflicting_information_detected
    THEN HUMAN_REVIEW

This module is that rule, applied to one AI-shadow Event at a time. It
sits ON TOP of two things that already exist rather than replacing them:

- A HARD exception may already be attached to the event itself (Day 3's
  mock-tool fault injection, surfaced through Day 8's shadow handlers —
  e.g. res_0009/res_0010's `missing_document`/`unexpected_format`
  failures). This detector passes that straight through as the
  strongest possible signal: the step didn't just look risky, it
  actually failed.
- A SOFT signal — low confidence with no hard failure — is new to this
  module. Section 21's own illustrative threshold (<70% => human
  review) is reused here as `CONFIDENCE_THRESHOLD`, with the same
  caveat Section 21 states explicitly: this number is a starting point,
  not a tuned result, and Day 15's experiments are where it would get
  real evidence behind it.

HONEST CAVEAT: `conflicting_information_detected` is part of Section
17's rule and this detector checks for it (via an optional
`conflicting_information` flag an event's `input` dict may carry), but
no case in this project's 12-resume dataset currently exercises it —
Day 3/4 never generated a demonstration with genuinely conflicting
information. The check is real, not decorative (a unit test proves it
fires when the flag is present), but the real-data run in
`build_investigation.py` will honestly report zero cases of this
specific trigger, same as Day 9 reported zero real disagreements.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

CONFIDENCE_THRESHOLD = 0.70  # Section 21's own illustrative "<70% => human review" cutoff


@dataclass(frozen=True)
class DetectedException:
    event_id: str
    demo_id: str
    action: str
    trigger: str  # "hard_failure" | "low_confidence" | "missing_data" | "conflicting_information"
    exception_type: Optional[str]  # from schemas.event.ExceptionType, when known
    confidence: Optional[float]
    reason: str
    forces_human_review: bool


def detect(event: dict) -> Optional[DetectedException]:
    """Returns a DetectedException if this event trips any of Section
    17's three triggers, else None. Checks in priority order: a hard
    failure (strongest signal) first, then the two soft triggers.
    """
    event_id = event.get("event_id", "")
    demo_id = event.get("demo_id", "")
    action = event.get("action", "")
    confidence = event.get("confidence")

    # Trigger 1: the step actually failed — a hard exception is already attached.
    if event.get("result") == "failure":
        exc = event.get("exception") or {}
        return DetectedException(
            event_id=event_id,
            demo_id=demo_id,
            action=action,
            trigger="hard_failure",
            exception_type=exc.get("exception_type"),
            confidence=confidence,
            reason=f"Step failed: {exc.get('description', 'no description recorded')}",
            forces_human_review=True,
        )

    # Trigger 2: required_data_missing — the step "succeeded" but produced an empty
    # output where this workflow always expects real fields back (a softer cousin of
    # trigger 1: the call didn't raise, but there's nothing usable to act on).
    output = event.get("output") or {}
    data_actions = {"fetch_resume", "extract_resume"}
    if action in data_actions and event.get("result") == "success" and not output:
        return DetectedException(
            event_id=event_id,
            demo_id=demo_id,
            action=action,
            trigger="missing_data",
            exception_type="missing_document",
            confidence=confidence,
            reason=f"{action} returned success with an empty output — required data is missing.",
            forces_human_review=True,
        )

    # Trigger 3: conflicting_information_detected — see HONEST CAVEAT above.
    if (event.get("input") or {}).get("conflicting_information"):
        return DetectedException(
            event_id=event_id,
            demo_id=demo_id,
            action=action,
            trigger="conflicting_information",
            exception_type="conflicting_information",
            confidence=confidence,
            reason="Input is flagged as containing conflicting information.",
            forces_human_review=True,
        )

    # Trigger 4 (soft): confidence < threshold, with no hard failure.
    if confidence is not None and confidence < CONFIDENCE_THRESHOLD:
        return DetectedException(
            event_id=event_id,
            demo_id=demo_id,
            action=action,
            trigger="low_confidence",
            exception_type="ambiguous_decision",
            confidence=confidence,
            reason=f"Confidence {confidence:.2f} is below the {CONFIDENCE_THRESHOLD:.2f} review threshold.",
            forces_human_review=True,
        )

    return None


def detect_all(events: list[dict]) -> list[DetectedException]:
    detected = []
    for e in events:
        d = detect(e)
        if d is not None:
            detected.append(d)
    return detected
