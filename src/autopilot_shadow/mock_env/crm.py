"""
Mock CRM: candidate record storage.

Record writes are reversible (Section 10 factor: reversibility) — this is
what makes "update candidate record" a lower-risk step than "send email"
in the risk model (Day 10). CRM writes ARE tracked in an audit log so a
correction (Day 12) can be traced back to the record it changed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .faults import FaultType, maybe_raise


@dataclass
class CandidateRecord:
    resume_id: str
    candidate_name: str
    status: str  # e.g. "new", "shortlisted", "rejected", "under_review"
    notes: str = ""
    history: list[dict] = field(default_factory=list)


class CRM:
    def __init__(self):
        self._records: dict[str, CandidateRecord] = {}

    def create_or_update_record(
        self,
        resume_id: str,
        candidate_name: str,
        status: str,
        notes: str = "",
        fault: FaultType = FaultType.NONE,
    ) -> CandidateRecord:
        maybe_raise(fault)

        if not resume_id or not candidate_name:
            from .faults import MalformedInputError

            raise MalformedInputError("CRM update requires resume_id and candidate_name.")

        record = self._records.get(resume_id)
        if record is None:
            record = CandidateRecord(resume_id=resume_id, candidate_name=candidate_name, status=status, notes=notes)
        else:
            record.history.append(
                {"timestamp": datetime.now().isoformat(), "previous_status": record.status, "previous_notes": record.notes}
            )
            record.status = status
            record.notes = notes

        self._records[resume_id] = record
        return record

    def get_record(self, resume_id: str) -> CandidateRecord | None:
        return self._records.get(resume_id)

    def all_records(self) -> list[CandidateRecord]:
        return list(self._records.values())
