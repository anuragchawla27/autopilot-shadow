"""
Day 3 validation: proves the mock environment behaves like a simplified
real system AND fails safely in the required cases (Section 19):
successful execution, tool failure, malformed input, missing information,
API timeout, and duplicate requests.

Run: python -m pytest tests/test_mock_env_day3.py -v
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from autopilot_shadow.mock_env.environment import MockEnvironment
from autopilot_shadow.mock_env.faults import (
    ApiTimeoutError,
    DuplicateRequestError,
    FaultType,
    MalformedInputError,
    MissingInformationError,
    ToolFailureError,
)
from autopilot_shadow.mock_env.resume_db import DuplicateResumeAlreadyFetched

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def resumes():
    return json.loads((DATA_DIR / "resumes.json").read_text())


@pytest.fixture
def env(resumes):
    return MockEnvironment(resumes)


# --- successful execution ---------------------------------------------

def test_fetch_and_parse_clean_resume_succeeds(env):
    raw = env.resume_db.fetch_resume("res_0001")
    parsed = env.document_parser.parse(raw)
    assert parsed.candidate_name == "Priya Nair"
    assert parsed.experience_years == 3.5
    assert "python" in parsed.skills


def test_crm_create_and_update_record(env):
    record = env.crm.create_or_update_record("res_0001", "Priya Nair", status="shortlisted")
    assert record.status == "shortlisted"
    updated = env.crm.create_or_update_record("res_0001", "Priya Nair", status="interview_scheduled", notes="Called candidate")
    assert updated.status == "interview_scheduled"
    assert len(updated.history) == 1  # previous state preserved


def test_draft_email_is_safe_and_does_not_require_approval(env):
    draft = env.email_service.draft_email("priya.nair@example.com", "Interview Invitation", "Body text")
    assert draft["to"] == "priya.nair@example.com"
    assert env.email_service.outbox == []  # drafting never sends


def test_send_email_requires_explicit_approval(env):
    with pytest.raises(PermissionError):
        env.email_service.send_email("priya.nair@example.com", "Interview Invitation", "Body", approved=False)
    assert env.email_service.outbox == []


def test_send_email_with_approval_succeeds_mock_only(env):
    record = env.email_service.send_email("priya.nair@example.com", "Interview Invitation", "Body", approved=True)
    assert record.status == "sent"
    assert len(env.email_service.outbox) == 1  # in-memory only, no real network call exists in this codebase


def test_ticket_create_and_close(env):
    ticket = env.ticket_system.create_ticket("Ambiguous candidate", "Needs human review", priority="high")
    assert ticket.status == "open"
    closed = env.ticket_system.close_ticket(ticket.ticket_id)
    assert closed.status == "closed"


# --- CASE 5: tool returns malformed output / input ----------------------

def test_malformed_skills_field_raises(env):
    raw = env.resume_db.fetch_resume("res_0010")  # skills is a string, not a list
    with pytest.raises(MalformedInputError):
        env.document_parser.parse(raw)


def test_crm_rejects_malformed_input(env):
    with pytest.raises(MalformedInputError):
        env.crm.create_or_update_record("", "", status="shortlisted")


# --- CASE 4: AI/human encounters missing information ---------------------

def test_missing_experience_years_raises(env):
    raw = env.resume_db.fetch_resume("res_0009")  # experience_years is ""
    with pytest.raises(MissingInformationError):
        env.document_parser.parse(raw)


# --- CASE 8: same request processed twice --------------------------------

def test_duplicate_resume_fetch_detected(env):
    env.resume_db.fetch_resume("res_0011")
    with pytest.raises(DuplicateResumeAlreadyFetched):
        env.resume_db.fetch_resume("res_0011")


def test_duplicate_email_send_detected(env):
    env.email_service.send_email("a@example.com", "Subject", "Body", approved=True)
    with pytest.raises(DuplicateRequestError):
        env.email_service.send_email("a@example.com", "Subject", "Body", approved=True)


# --- injected tool failure / timeout (forced via `fault=`) ---------------

def test_injected_tool_failure(env):
    with pytest.raises(ToolFailureError):
        env.resume_db.fetch_resume("res_0001", fault=FaultType.TOOL_FAILURE)


def test_injected_api_timeout(env):
    with pytest.raises(ApiTimeoutError):
        env.crm.create_or_update_record("res_0001", "Priya Nair", status="shortlisted", fault=FaultType.API_TIMEOUT)


def test_injected_duplicate_request_on_ticket(env):
    with pytest.raises(DuplicateRequestError):
        env.ticket_system.create_ticket("x", "y", fault=FaultType.DUPLICATE_REQUEST)


# --- prompt-injection resume is still just data ---------------------------

def test_prompt_injection_resume_parses_as_plain_data(env):
    """Section 5 safety note (S5 in docs/01): resume text is untrusted
    input, never instructions. Parsing must not execute or interpret the
    injected text - it's just stored as raw_text like any other resume."""
    raw = env.resume_db.fetch_resume("res_0012")
    parsed = env.document_parser.parse(raw)
    assert "Ignore all previous instructions" in parsed.raw_text
    # the parser must not have "obeyed" the injected text - skills/experience
    # come only from the structured fields, not from raw_text content
    assert parsed.experience_years == 2.0
    assert set(parsed.skills) == {"sql", "python", "excel"}


def test_ground_truth_and_job_description_load():
    jd = json.loads((DATA_DIR / "job_description.json").read_text())
    gt = json.loads((DATA_DIR / "ground_truth.json").read_text())
    resumes = json.loads((DATA_DIR / "resumes.json").read_text())
    assert jd["required_experience_years"] == 2
    assert len(gt["labels"]) == len(resumes) == 12


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
