"""
Mock resume database + document parser.

Stands in for two of the brief's Section 19 tools (resume database,
document parser) since in this project they're always used together:
a resume is fetched, then parsed into structured fields.

Everything here is synthetic. See data/resumes.json.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .faults import FaultType, maybe_raise


@dataclass
class ParsedResume:
    resume_id: str
    candidate_name: str
    email: str
    experience_years: float
    skills: list[str]
    education: str
    raw_text: str


class ResumeDatabase:
    """In-memory store of synthetic resumes, keyed by resume_id."""

    def __init__(self, resumes: list[dict]):
        self._store: dict[str, dict] = {r["resume_id"]: r for r in resumes}
        self._processed: set[str] = set()  # tracks fetches, for duplicate detection

    def fetch_resume(self, resume_id: str, fault: FaultType = FaultType.NONE) -> dict:
        """Returns the raw resume record. Raises on injected faults."""
        maybe_raise(fault)

        if fault == FaultType.NONE and resume_id in self._processed:
            # Real duplicate check: same id fetched twice without an explicit
            # DUPLICATE_REQUEST fault also counts as a duplicate in practice.
            raise_dup = DuplicateResumeAlreadyFetched(resume_id)
            raise raise_dup

        if resume_id not in self._store:
            raise KeyError(f"No resume with id {resume_id!r}")

        self._processed.add(resume_id)
        return self._store[resume_id]

    def reset(self) -> None:
        """Clears the duplicate-tracking state (used between test cases)."""
        self._processed.clear()


class DuplicateResumeAlreadyFetched(Exception):
    """Raised when the same resume_id is fetched twice in one session
    without the caller explicitly acknowledging it via DUPLICATE_REQUEST.
    Kept separate from FaultType.DUPLICATE_REQUEST because this one is
    detected by the tool itself (stateful), not injected by the caller.
    """

    def __init__(self, resume_id: str):
        super().__init__(f"resume_id {resume_id!r} was already fetched in this session (possible duplicate submission).")
        self.resume_id = resume_id


class DocumentParser:
    """Extracts structured fields from a raw resume record.

    A resume missing required fields (e.g. no 'skills' key, or an
    unparseable free-text body) is the natural source of
    MALFORMED_INPUT / MISSING_INFORMATION faults, in addition to the
    faults a caller can force explicitly.
    """

    REQUIRED_FIELDS = ("candidate_name", "email", "experience_years", "skills", "education", "raw_text")

    def parse(self, raw_resume: dict, fault: FaultType = FaultType.NONE) -> ParsedResume:
        maybe_raise(fault)

        missing = [f for f in self.REQUIRED_FIELDS if f not in raw_resume or raw_resume[f] in (None, "")]
        if missing:
            from .faults import MissingInformationError

            raise MissingInformationError(f"Resume {raw_resume.get('resume_id', '?')!r} is missing fields: {missing}")

        if not isinstance(raw_resume.get("skills"), list):
            from .faults import MalformedInputError

            raise MalformedInputError(f"Resume {raw_resume.get('resume_id', '?')!r} has a malformed 'skills' field.")

        return ParsedResume(
            resume_id=raw_resume["resume_id"],
            candidate_name=raw_resume["candidate_name"],
            email=raw_resume["email"],
            experience_years=float(raw_resume["experience_years"]),
            skills=list(raw_resume["skills"]),
            education=raw_resume["education"],
            raw_text=raw_resume["raw_text"],
        )
