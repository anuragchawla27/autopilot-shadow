"""
Mock ticket/notification system — used for escalations and human-review
queues (Section 18: ESCALATE gate outcome).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .faults import FaultType, maybe_raise


@dataclass
class Ticket:
    ticket_id: str
    subject: str
    description: str
    priority: str  # "low" | "medium" | "high"
    status: str = "open"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class TicketSystem:
    def __init__(self):
        self._tickets: dict[str, Ticket] = {}
        self._counter = 0

    def create_ticket(
        self, subject: str, description: str, priority: str = "medium", fault: FaultType = FaultType.NONE
    ) -> Ticket:
        maybe_raise(fault)
        if priority not in ("low", "medium", "high"):
            from .faults import MalformedInputError

            raise MalformedInputError(f"Invalid priority: {priority!r}")

        self._counter += 1
        ticket = Ticket(ticket_id=f"tkt_{self._counter:04d}", subject=subject, description=description, priority=priority)
        self._tickets[ticket.ticket_id] = ticket
        return ticket

    def get_ticket(self, ticket_id: str) -> Ticket | None:
        return self._tickets.get(ticket_id)

    def close_ticket(self, ticket_id: str, fault: FaultType = FaultType.NONE) -> Ticket:
        maybe_raise(fault)
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            raise KeyError(f"No ticket with id {ticket_id!r}")
        ticket.status = "closed"
        return ticket
