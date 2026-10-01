"""
Day 6 validation: proves the decision extraction engine independently
re-derives sensible rules from the raw event log (not from the Day 4
generator's source code), correctly separates explicit/inferred/unknown,
and never fabricates confidence where evidence is thin.

Run: python -m pytest tests/test_decision_extraction_day6.py -v
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from autopilot_shadow.decisions.extraction import MIN_EVIDENCE_FOR_INFERENCE, extract_rules
from autopilot_shadow.schemas.workflow import RuleType

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def events():
    return json.loads((DATA_DIR / "demonstrations.json").read_text())


@pytest.fixture
def job_description():
    return json.loads((DATA_DIR / "job_description.json").read_text())


@pytest.fixture
def rules(events, job_description):
    return extract_rules(events, job_description)


def test_every_rule_has_a_type_no_rule_left_unlabelled(rules):
    """Section 8 is mandatory: every decision must be explicit/inferred/unknown."""
    for r in rules:
        assert r.rule_type in (RuleType.EXPLICIT, RuleType.INFERRED, RuleType.UNKNOWN)


def test_experience_threshold_rule_is_explicit(rules, job_description):
    explicit_rules = [r for r in rules if r.rule_type == RuleType.EXPLICIT]
    assert len(explicit_rules) == 2
    thresholds = [r for r in explicit_rules if r.then_outcome == "reject"]
    assert len(thresholds) == 1
    assert thresholds[0].evidence_count == 2  # res_0002, res_0005
    # the rule's condition value must come from the JD config, not a hardcoded guess
    assert thresholds[0].conditions[0].value == job_description["required_experience_years"]


def test_full_skill_match_rule_is_explicit(rules, job_description):
    explicit_rules = [r for r in rules if r.rule_type == RuleType.EXPLICIT]
    shortlist_rule = [r for r in explicit_rules if r.then_outcome == "shortlist"]
    assert len(shortlist_rule) == 1
    # res_0001, res_0003, res_0006, res_0011 (plain) + res_0011 (dup demo) = 5
    assert shortlist_rule[0].evidence_count == 5


def test_single_example_patterns_are_unknown_not_inferred(rules):
    """Core honesty check: with only 1 supporting demo, the engine must
    NOT claim 'inferred' confidence, even though the single example is
    internally consistent."""
    unknown_rules = [r for r in rules if r.rule_type == RuleType.UNKNOWN]
    assert len(unknown_rules) == 4
    for r in unknown_rules:
        assert r.evidence_count < MIN_EVIDENCE_FOR_INFERENCE


def test_no_rule_claims_inferred_without_minimum_evidence(rules):
    for r in rules:
        if r.rule_type == RuleType.INFERRED:
            assert r.evidence_count >= MIN_EVIDENCE_FOR_INFERENCE


def test_prompt_injection_case_is_unknown_to_the_extraction_engine(rules):
    """This is a deliberate, documented finding: the engine has no way to
    know the injection-override was a deliberate safety rule, because
    that policy isn't exposed as explicit config anywhere it can see.
    From pure evidence, n=1 is correctly UNKNOWN, not a confident rule."""
    injection_rules = [r for r in rules if "injection_detected=True" in r.description]
    assert len(injection_rules) == 1
    assert injection_rules[0].rule_type == RuleType.UNKNOWN
    assert injection_rules[0].evidence_count == 1


def test_contradictory_evidence_would_be_unknown_not_averaged():
    """Synthetic unit check: if the SAME evidence combination produced
    DIFFERENT outcomes across demos, the engine must call it UNKNOWN
    (contradictory), never silently pick a majority outcome and label
    it confident."""
    fake_events = [
        {
            "demo_id": "demo_a",
            "action": "classify_candidate",
            "input": {"experience_ok": True, "skill_match_tier": "partial", "injection_detected": False},
            "decision": {"outcome": "human_review"},
        },
        {
            "demo_id": "demo_b",
            "action": "classify_candidate",
            "input": {"experience_ok": True, "skill_match_tier": "partial", "injection_detected": False},
            "decision": {"outcome": "shortlist"},  # contradicts demo_a with identical evidence
        },
    ]
    fake_jd = {"required_experience_years": 2, "required_skills": ["sql", "python", "excel"]}
    result = extract_rules(fake_events, fake_jd)
    partial_rules = [r for r in result if "skill_match_tier='partial'" in r.description]
    assert len(partial_rules) == 1
    assert partial_rules[0].rule_type == RuleType.UNKNOWN
    assert partial_rules[0].then_outcome == "contradictory"


def test_extraction_does_not_import_human_demo_policy():
    """Structural proof of independence: the extraction module must not
    IMPORT the Day 4 generator's decision logic (a docstring mentioning
    it by name, to explain the independence, is fine - only an actual
    import/dependency would be circular)."""
    import ast

    import autopilot_shadow.decisions.extraction as extraction_module

    src = Path(extraction_module.__file__).read_text()
    tree = ast.parse(src)
    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)

    assert not any("human_demo" in m for m in imported_modules)


def test_rules_attach_cleanly_to_reconstructed_workflow(rules):
    from autopilot_shadow.schemas.workflow import Workflow

    workflow = Workflow.model_validate_json((DATA_DIR / "reconstructed_workflow_v1.json").read_text())
    classify_step = next(s for s in workflow.steps if s.action == "classify_candidate")
    classify_step.rules = rules
    assert len(classify_step.rules) == 6
    # round-trip through JSON to confirm it's actually serializable (S7 - real output, not a mock)
    dumped = workflow.model_dump_json()
    reloaded = Workflow.model_validate_json(dumped)
    assert len(reloaded.get_step(classify_step.id).rules) == 6


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
