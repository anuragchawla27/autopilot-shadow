"""
MockEnvironment — bundles all mock tools into one object so the event
logger (Day 4) and shadow engine (Day 8) have a single, resettable handle
on the sandbox instead of importing five separate tools everywhere.
"""

from __future__ import annotations

from .crm import CRM
from .email_service import EmailService
from .resume_db import DocumentParser, ResumeDatabase
from .ticket_system import TicketSystem


class MockEnvironment:
    def __init__(self, resumes: list[dict]):
        self.resume_db = ResumeDatabase(resumes)
        self.document_parser = DocumentParser()
        self.crm = CRM()
        self.email_service = EmailService()
        self.ticket_system = TicketSystem()

    def reset(self, resumes: list[dict] | None = None) -> None:
        """Fresh environment for a new demonstration/experiment run."""
        self.resume_db = ResumeDatabase(resumes if resumes is not None else list(self.resume_db._store.values()))
        self.crm = CRM()
        self.email_service = EmailService()
        self.ticket_system = TicketSystem()
