"""
Day 14 validation: Section 23's 10 required failure scenarios all fail
safely, plus the two pieces of new Day 14 engineering they depend on —
the tool output-contract check (closes Section 20's gap, Case 2) and
the calibration report (Case 3).

Run: python -m pytest tests/test_failure_scenarios_day14.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from autopilot_shadow.failure_scenarios import scenarios
from autopilot_shadow.failure_scenarios.calibration import (
    calibration_report,
    high_confidence_wrong_is_still_safe,
)
from autopilot_shadow.failure_scenarios.tool_contracts import validate_output
from autopilot_shadow.failure_scenarios.wrong_tool_harness import run_wrong_tool_for_fetch_resume
from autopilot_shadow.mock_env.environment import MockEnvironment


@pytest.fixture
def resumes():
    import json

    data_dir = Path(__file__).resolve().parents[1] / "data"
    return json.loads((data_dir / "resumes.json").read_text())


@pytest.fixture
def env(resumes):
    return MockEnvironment(resumes)


# --- tool_contracts.py (new) ---------------------------------------------

def test_validate_output_passes_a_well_shaped_fetch_resume_output():
    good = {"resume_id": "res_0001", "candidate_name": "Priya Nair", "skills": ["python"]}
    assert validate_output("fetch_resume", good) is None


def test_validate_output_flags_a_missing_required_key():
    bad = {"ticket_id": "tkt_0001", "status": "open"}
    violation = validate_output("fetch_resume", bad)
    assert violation is not None
    assert violation.missing_keys == {"resume_id", "candidate_name", "skills"}


def test_validate_output_requires_a_known_action():
    with pytest.raises(KeyError):
        validate_output("not_a_real_action", {})


# --- wrong_tool_harness.py (new, Case 2) -----------------------------------

def test_wrong_tool_for_fetch_resume_is_caught(env):
    result = run_wrong_tool_for_fetch_resume(env, resume_id="res_0001")
    assert result.wrong_tool_called == "ticket_system.create_ticket"
    assert result.caught is True
    assert result.violation is not None
    assert "resume_id" in result.violation.missing_keys


# --- calibration.py (new, Case 3) ------------------------------------------

def test_calibration_report_runs_against_real_data():
    report = calibration_report()
    assert report.n_cases > 0
    assert 0.0 <= report.expected_calibration_error <= 1.0
    assert "ground_truth" in report.caveat
    assert "D-043" in report.caveat or "author" in report.caveat


def test_high_confidence_wrong_is_still_blocked_by_hard_override():
    result = high_confidence_wrong_is_still_safe()
    assert result.forced_confidence == 0.95
    assert result.recommendation == "approval_required"
    assert result.gate_required is True
    assert result.passed is True


# --- scenarios.py: all 10 Section 23 cases ---------------------------------

@pytest.mark.parametrize("case_fn", scenarios.ALL_CASES, ids=[c.__name__ for c in scenarios.ALL_CASES])
def test_each_failure_scenario_fails_safely(case_fn):
    result = case_fn()
    assert result.passed, f"{result.case_id} ({result.name}) did not fail safely: {result.observed}"


def test_run_all_returns_all_ten_cases_and_all_pass():
    results = scenarios.run_all()
    assert len(results) == 10
    assert {r.case_id for r in results} == {f"case_{i}" for i in range(1, 11)}
    assert all(r.passed for r in results)


def test_no_scenario_ever_calls_send_email():
    """Structural safety check, same pattern as Day 8's shadow_handlers.py
    proof: none of the failure scenarios' own source should call the real
    send_email method — only draft_email is ever safe to call here."""
    import ast
    import inspect

    source = inspect.getsource(scenarios)
    tree = ast.parse(source)
    calls = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert "send_email" not in calls
