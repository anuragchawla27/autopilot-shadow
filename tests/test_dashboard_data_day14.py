"""
Day 14 validation: the dashboard's data-loading layer reads every
real results/data file Section 32 asks for, without needing Streamlit
installed (data_loader.py is deliberately Streamlit-free).

Run: python -m pytest tests/test_dashboard_data_day14.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from dashboard import data_loader


def test_load_workflow_structure_returns_real_steps():
    wf = data_loader.load_workflow_structure()
    assert wf is not None
    assert wf["workflow_name"] == "resume_screening"
    assert len(wf["steps"]) > 0


def test_load_shadow_run_returns_real_events():
    events = data_loader.load_shadow_run()
    assert len(events) == 74  # Day 8's own documented count


def test_load_comparisons_returns_one_entry_per_resume():
    comparisons = data_loader.load_comparisons()
    assert len(comparisons) == 12


def test_load_readiness_matches_day13_headline():
    readiness = data_loader.load_readiness()
    assert readiness is not None
    assert readiness["shadow_score"]["shadow_score"] == 74.24
    assert readiness["readiness_decision"]["tier"] == "HUMAN_IN_THE_LOOP_READY"


def test_load_disagreements_is_honestly_empty():
    # D-054's real finding: 0 real disagreements in the 12-resume dataset.
    assert data_loader.load_disagreements() == []


def test_load_risk_scores_returns_74_cases():
    assert len(data_loader.load_risk_scores()) == 74


def test_load_corrections_are_all_tagged_simulated_demo():
    corrections = data_loader.load_corrections()
    assert len(corrections) > 0
    for c in corrections:
        assert c.get("source") == "simulated_demo"


def test_load_workflow_versions_v4_not_reached():
    versions = data_loader.load_workflow_versions()
    assert len(versions) == 4
    v4 = next(v for v in versions if v["version"] == 4)
    assert v4["reached"] is False


def test_load_failure_scenarios_returns_day14s_own_report():
    report = data_loader.load_failure_scenarios()
    assert report is not None
    assert report["n_cases"] == 10
    assert report["all_passed"] is True


def test_risk_distribution_counts_sum_to_total_cases():
    risk_scores = data_loader.load_risk_scores()
    dist = data_loader.risk_distribution(risk_scores)
    assert sum(dist.values()) == len(risk_scores)


def test_all_loaded_has_no_missing_keys():
    loaded = data_loader.all_loaded()
    expected_keys = {
        "workflow", "shadow_run", "comparisons", "agreement_scores",
        "disagreements", "readiness", "risk_scores", "corrections",
        "versions", "failure_scenarios",
    }
    assert set(loaded.keys()) == expected_keys
    for key, value in loaded.items():
        assert value is not None, f"{key} loaded as None — a results file is missing or misnamed"
