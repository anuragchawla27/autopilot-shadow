"""
Case 2 harness — "AI selects incorrect tool" (Day 14, Section 23).

HONEST NOTE ON WHY THIS IS A HARNESS, NOT A BUG REPRODUCTION: this
workflow's real action-to-tool mapping (fetch_resume -> resume_db,
check_experience -> pure computation, update_candidate_record -> crm,
send_interview_invitation -> email_service) is fixed and 1:1 — there is
no branch point anywhere in `generator/handlers.py` or
`shadow/shadow_handlers.py` where the system actually chooses between
multiple tools for the same action, so there is no real code path that
could organically select the wrong one. Rather than fabricate a fake
bug, this module deliberately constructs the wrong-tool case — calling
`ticket_system.create_ticket(...)` where `fetch_resume` should call
`resume_db.fetch_resume(...)` — and proves that `tool_contracts.py`'s
output check (Section 20's "validate outputs") catches it before any
downstream step would ever see the mismatched data.
"""

from __future__ import annotations

from dataclasses import dataclass

from autopilot_shadow.mock_env.environment import MockEnvironment

from .tool_contracts import ContractViolation, validate_output


@dataclass(frozen=True)
class WrongToolResult:
    action: str
    wrong_tool_called: str
    raw_output: dict
    violation: ContractViolation | None
    caught: bool


def run_wrong_tool_for_fetch_resume(env: MockEnvironment, resume_id: str = "res_0001") -> WrongToolResult:
    """Simulates the AI selecting `ticket_system` instead of `resume_db`
    for the `fetch_resume` action, then runs the real output-contract
    check against it."""
    ticket = env.ticket_system.create_ticket(
        subject=f"Wrong tool call for {resume_id}",
        description="Deliberately wrong tool selection for Case 2.",
    )
    raw_output = {
        "ticket_id": ticket.ticket_id,
        "subject": ticket.subject,
        "description": ticket.description,
        "priority": ticket.priority,
        "status": ticket.status,
    }
    violation = validate_output("fetch_resume", raw_output)
    return WrongToolResult(
        action="fetch_resume",
        wrong_tool_called="ticket_system.create_ticket",
        raw_output=raw_output,
        violation=violation,
        caught=violation is not None,
    )
