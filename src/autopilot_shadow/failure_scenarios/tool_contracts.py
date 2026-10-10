"""
Tool output contracts (Day 14, closes a gap in Section 20).

Section 20 ("Tool Orchestration") asks the system to "validate inputs
and outputs" of whichever tool it selects. Days 2-13 built real,
working mock tools (Day 3) and a real event logger that captures
whatever a tool returns (Day 4), but nothing in the codebase actually
checked that a tool's OUTPUT SHAPE matches what the next step expects.
That gap is harmless as long as every step always calls the right
tool — which is all the real 12-resume dataset ever exercises — but it
means the system had no way to notice Section 23's Case 2 ("AI selects
incorrect tool") on its own. This module is the fix: a small, explicit
contract per action (the output keys that action's result must carry)
and a validator that checks any result against it.

This is intentionally NOT schema validation of the whole Event (Day 2's
Pydantic model already does that) — it's narrower: "does THIS action's
output look like what a correctly-chosen tool for this action would
produce," independent of whether the call itself raised an exception.
A wrong tool can easily return a well-formed dict that is simply
missing the fields this workflow needs next.
"""

from __future__ import annotations

from dataclasses import dataclass

# The minimum set of keys this workflow's downstream steps actually read
# from each action's output, in the REAL handlers (generator/handlers.py,
# shadow/shadow_handlers.py). Deliberately a minimum, not an exhaustive
# schema — the point is detecting "this clearly isn't what this step
# produces," not re-implementing Pydantic.
EXPECTED_OUTPUT_KEYS: dict[str, set[str]] = {
    "fetch_resume": {"resume_id", "candidate_name", "skills"},
    "extract_resume": {"resume_id", "candidate_name", "experience_years", "skills"},
    "check_experience": {"experience_ok"},
    "compare_skills": {"match_tier"},
    "classify_candidate": {"classification"},
    "update_candidate_record": {"status"},
    "send_interview_invitation": set(),  # drafted email dict shape varies; see note below
}


@dataclass(frozen=True)
class ContractViolation:
    action: str
    missing_keys: set[str]
    actual_keys: set[str]
    reason: str


def validate_output(action: str, output: dict) -> ContractViolation | None:
    """Returns a ContractViolation if `output` is missing any key this
    action's real downstream steps depend on, else None.

    Known gap: `send_interview_invitation`'s drafted-email shape isn't
    checked here (its keys legitimately vary by caller) — Case 2's
    demonstration below targets `fetch_resume`, where the contract is
    unambiguous and the mismatch is easy to show plainly.
    """
    expected = EXPECTED_OUTPUT_KEYS.get(action)
    if expected is None:
        raise KeyError(f"No output contract defined for action {action!r} — tool_contracts.py must cover every action")
    if not expected:
        return None

    actual = set(output.keys())
    missing = expected - actual
    if missing:
        return ContractViolation(
            action=action,
            missing_keys=missing,
            actual_keys=actual,
            reason=f"Output for {action!r} is missing required key(s) {sorted(missing)} — "
            f"this does not look like what {action!r} is supposed to produce.",
        )
    return None
