"""
Day 15 validation: Ablation Systems A-E (Section 31), run against the
real 12-resume dataset.

Run: python -m pytest tests/test_ablation_day15.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from autopilot_shadow.experiments import ablation_engine
from autopilot_shadow.experiments.bare_decision import bare_classify, bare_decide_everything


# --- bare_decision.py --------------------------------------------------------

def test_bare_classify_has_no_injection_check_and_wrongly_shortlists_res_0012():
    """The one deliberately adversarial resume in this dataset (Section
    17/S5's own test case): meets every surface threshold, but only the
    real classifier's injection check catches it. Proves the bare
    decision is missing exactly that, not just asserting it."""
    import json

    data_dir = Path(__file__).resolve().parents[1] / "data"
    resumes = {r["resume_id"]: r for r in json.loads((data_dir / "resumes.json").read_text())}
    jd = json.loads((data_dir / "job_description.json").read_text())

    from autopilot_shadow.mock_env.environment import MockEnvironment

    env = MockEnvironment(list(resumes.values()))
    ctx = {"resume_id": "res_0012"}
    output, decision = bare_decide_everything(ctx, env, jd)
    assert output["classification"] == "shortlist"  # WRONG — ground truth says human_review
    assert "injection" not in decision.evidence.get("reason", "").lower()


# --- ablation_executors.py / ablation_engine.py -----------------------------

def test_system_a_has_no_per_step_structure():
    result = ablation_engine.run_system_a()
    # One combined decision event + at most 2 mechanical steps = 3, never the
    # full 6-7 a structured executor produces.
    assert all(c["steps_executed"] <= 3 for c in result["cases"])


def test_system_b_uses_identical_decision_logic_to_system_a():
    """Systems A and B must reach the SAME classification per case — the
    ablation variable between them is architecture (steps_executed), not
    the decision itself."""
    a = ablation_engine.run_system_a()
    b = ablation_engine.run_system_b()
    a_by_id = {c["resume_id"]: c["final_action"] for c in a["cases"]}
    b_by_id = {c["resume_id"]: c["final_action"] for c in b["cases"]}
    assert a_by_id == b_by_id
    # ...but B's structure gives real per-step traceability A doesn't have.
    assert b["metrics"]["avg_steps_executed"] > a["metrics"]["avg_steps_executed"]


def test_systems_a_and_b_both_misclassify_the_injection_case():
    """The real, measured consequence of ablating the injection check —
    not a hypothetical, an actual wrong decision on a real case."""
    for result in (ablation_engine.run_system_a(), ablation_engine.run_system_b()):
        case = next(c for c in result["cases"] if c["resume_id"] == "res_0012")
        assert case["final_action"] == "shortlist"
        assert case["matches_ground_truth"] is False


def test_system_c_reuses_experiment_d_exactly():
    """Systems C (ablation) and D (experiment) are deliberately the SAME
    component, asked about from two different study angles — this proves
    they really are identical, not just similarly named."""
    from autopilot_shadow.experiments import engine

    ablation_c = ablation_engine.run_system_c()["metrics"]
    experiment_d = engine.run_experiment_d()["metrics"]
    assert ablation_c == experiment_d


def test_system_d_reuses_experiment_e_exactly():
    from autopilot_shadow.experiments import engine

    ablation_d = ablation_engine.run_system_d()["metrics"]
    experiment_e = engine.run_experiment_e()["metrics"]
    assert ablation_d == experiment_e


def test_system_e_has_zero_false_automation_and_zero_unsafe_sends():
    result = ablation_engine.run_system_e()
    m = result["metrics"]
    assert m["false_automation"] == 0
    assert m["unsafe_invitations_sent"] == 0


def test_system_e_documents_qualitative_additions_over_system_d():
    result = ablation_engine.run_system_e()
    assert len(result["qualitative_additions_over_system_d"]) > 0
    for item in result["qualitative_additions_over_system_d"]:
        assert "capability" in item and "evidence" in item


def test_false_automation_strictly_decreases_from_system_a_to_system_c():
    """The headline ablation finding: injection-check + confidence
    together eliminate the one real false automation A/B produce."""
    a = ablation_engine.run_system_a()["metrics"]
    c = ablation_engine.run_system_c()["metrics"]
    assert a["false_automation"] == 1
    assert c["false_automation"] == 0


def test_run_all_returns_five_systems_in_order():
    results = ablation_engine.run_all()
    assert [r["system"] for r in results] == ["A", "B", "C", "D", "E"]
    for r in results:
        assert r["metrics"]["n_cases"] == 12
