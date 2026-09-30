"""
Mock email service — the canonical HIGH-RISK, IRREVERSIBLE tool in this
project (Section 22: "Never allow the system to send real emails without
explicit approval").

CRITICAL SAFEGUARD: `send_email` only ever appends to an in-memory
outbox. There is no SMTP client, no network call, and no code path here
that can reach a real mail server. In shadow mode (Day 8), the AI is only
ever allowed to call `draft_email` — `send_email` must sit behind a human
approval gate (Day 11) for the rest of the project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .faults import FaultType, maybe_raise


@dataclass
class EmailRecord:
    to: str
    subject: str
    body: str
    sent_at: str
    status: str  # "sent" (mock) — never a real delivery


class EmailService:
    def __init__(self):
        self.outbox: list[EmailRecord] = []
        self._sent_keys: set[tuple[str, str]] = set()  # (to, subject) for duplicate detection

    def draft_email(self, to: str, subject: str, body: str, fault: FaultType = FaultType.NONE) -> dict:
        """Prepares an email without sending it. Always safe to call — this
        is the only method the AI may call in shadow mode."""
        maybe_raise(fault)
        if not to or "@" not in to:
            from .faults import MalformedInputError

            raise MalformedInputError(f"Invalid recipient address: {to!r}")
        return {"to": to, "subject": subject, "body": body}

    def send_email(
        self, to: str, subject: str, body: str, approved: bool, fault: FaultType = FaultType.NONE
    ) -> EmailRecord:
        """Mock send — appends to an in-memory outbox only. Requires
        `approved=True`; this is the code-level enforcement of the human
        approval gate. No real network call is made anywhere in this
        method."""
        maybe_raise(fault)

        if not approved:
            raise PermissionError("send_email called without explicit human approval. Refusing.")

        if (to, subject) in self._sent_keys:
            from .faults import DuplicateRequestError

            raise DuplicateRequestError(f"An email to {to!r} with subject {subject!r} was already sent (mock).")

        record = EmailRecord(to=to, subject=subject, body=body, sent_at=datetime.now().isoformat(), status="sent")
        self.outbox.append(record)
        self._sent_keys.add((to, subject))
        return record
