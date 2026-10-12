"""
Day 15 — Ablation Systems A-E (Section 31), run over the real 12-resume
dataset. All 5 reduce to the same `CaseOutcome`/`aggregate` shape as
Experiments A-E (`case_outcome.py`) so the two studies are directly
comparable, and Systems C/D deliberately REUSE Experiment D/E's real
executors rather than reimplementing them — see each run_system_*'s
docstring for why.

  A — bare decision, no structure           (BareNoStructureExecutor)
  B — + workflow reconstruction              (BareStructuredExecutor)
  C — + confidence                           (ConfidenceOnlyExecutor — same as Experiment D)
  D — + risk model                           (RiskAwareExecutor — same as Experiment E)
  E — complete AUTOPILOT SHADOW system       (RiskAwareExecutor + qualitative note)
"""

from __future__ import annotations

import json
from pathlib import Path

from autopilot_shadow.mock_env.environment import MockEnvironment
from autopilot_shadow.schemas.workflow import Workflow

from .ablation_executors import BareNoStructureExecutor, BareStructuredExecutor
from .case_outcome import aggregate
from .confidence_only_executor import ConfidenceOnlyExecutor
from .engine import RESUME_IDS, _ground_truth, _job_description, _outcome_from_events, _resumes
from .risk_aware_executor import RiskAwareExecutor

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"


def _classified_workflow() -> Workflow:
    return Workflow.model_validate_json((DATA_DIR / "workflow_classified.json").read_text())


def _historical_agreement() -> dict:
    return json.loads((RESULTS_DIR / "day10_historical_agreement_by_action.json").read_text())


def _run_generic(system_id: str, name: str, description: str, run_fn, extra: dict | None = None) -> dict:
    resumes = _resumes()
    job_description = _job_description()
    ground_truth = _ground_truth()
    outcomes = []
    for resume_id in RESUME_IDS:
        env = MockEnvironment(resumes)
        logger = run_fn(env, job_description, resume_id)
        expected = ground_truth[resume_id]["expected_decision"]
        last_event = logger.events[-1] if logger.events else None
        halted = bool(last_event and last_event.approval == "pending")
        automated = bool(logger.events) and not any(e.result == "failure" for e in logger.events) and not halted
        outcomes.append(
            _outcome_from_events(
                resume_id=resume_id,
                expected_decision=expected,
                events=logger.events,
                automated=automated,
                halted_for_human=halted,
            )
        )
    result = {
        "system": system_id,
        "name": name,
        "description": description,
        "cases": [o.as_dict() for o in outcomes],
        "metrics": aggregate(outcomes),
    }
    if extra:
        result.update(extra)
    return result


# --- System A: bare decision, no structure --------------------------------
def run_system_a() -> dict:
    def _run(env, jd, resume_id):
        return BareNoStructureExecutor().run(env, jd, resume_id, demo_id=f"ablA_{resume_id}")

    return _run_generic(
        "A",
        "Bare decision only (no architecture)",
        "Section 31's 'LLM automation only' — honestly reframed since this project calls no LLM anywhere "
        "(D-009 open): the simplest possible opaque decision, same threshold logic as the real classifier "
        "but with NO prompt-injection check and NO per-step structure. See docs/18 and bare_decision.py.",
        _run,
    )


# --- System B: + workflow reconstruction ----------------------------------
def run_system_b() -> dict:
    workflow = _classified_workflow()

    def _run(env, jd, resume_id):
        return BareStructuredExecutor(workflow).run(env, jd, resume_id, demo_id=f"ablB_{resume_id}")

    return _run_generic(
        "B",
        "+ workflow reconstruction",
        "The SAME bare decision as System A, now run through the real reconstructed Workflow step by step. "
        "Isolates what structure alone contributes: per-step traceability (steps_executed), not correctness.",
        _run,
    )


# --- System C: + confidence --------------------------------------------------
def run_system_c() -> dict:
    workflow = _classified_workflow()

    def _run(env, jd, resume_id):
        return ConfidenceOnlyExecutor(workflow).run(env, jd, resume_id, demo_id=f"ablC_{resume_id}")

    return _run_generic(
        "C",
        "+ confidence",
        "Reuses Experiment D's real ConfidenceOnlyExecutor unchanged — this is deliberately the SAME "
        "component under both studies, not reimplemented, because it is genuinely the same ablation "
        "question (confidence added, no risk model yet) asked from two angles.",
        _run,
    )


# --- System D: + risk model -----------------------------------------------
def run_system_d() -> dict:
    workflow = _classified_workflow()
    hist = _historical_agreement()

    def _run(env, jd, resume_id):
        return RiskAwareExecutor(workflow, hist).run(env, jd, resume_id, demo_id=f"ablD_{resume_id}")

    return _run_generic(
        "D",
        "+ risk model",
        "Reuses Experiment E's real RiskAwareExecutor unchanged (Day 10's risk model + Day 11's gate logic).",
        _run,
    )


# --- System E: complete AUTOPILOT SHADOW system ---------------------------
def run_system_e() -> dict:
    workflow = _classified_workflow()
    hist = _historical_agreement()

    def _run(env, jd, resume_id):
        return RiskAwareExecutor(workflow, hist).run(env, jd, resume_id, demo_id=f"ablE_{resume_id}")

    return _run_generic(
        "E",
        "Complete AUTOPILOT SHADOW system",
        "At the per-case DECISION level, this is identical to System D — Days 7/10/11's risk-aware step "
        "walk already IS the project's real decision chain, so there is no different per-case outcome to "
        "show without inventing one. What 'complete system' actually adds beyond System D is not a "
        "different decision, but surrounding capability System D doesn't have: Day 11's full 4-state "
        "approval gate (approve/edit/reject/escalate, not just 'halted'), Day 12's correction memory, and "
        "Day 13's decomposable readiness assessment. See the 'qualitative_additions' field for where each "
        "of those is evidenced for real.",
        _run,
        extra={
            "qualitative_additions_over_system_d": [
                {"capability": "4-state human approval gate (not just halt)", "evidence": "results/day11_approval_queue.json"},
                {"capability": "disagreement investigation records", "evidence": "results/day11_disagreements.json"},
                {"capability": "correction memory", "evidence": "results/day12_correction_memory.json"},
                {"capability": "workflow versioning (V1-V4)", "evidence": "results/day12_workflow_versions.json"},
                {"capability": "decomposable automation-readiness score + tiered decision", "evidence": "results/day13_readiness_assessment.json"},
                {"capability": "10 Section-23 failure scenarios proven to fail safely", "evidence": "results/day14_failure_scenarios.json"},
            ]
        },
    )


ALL_SYSTEMS = [run_system_a, run_system_b, run_system_c, run_system_d, run_system_e]


def run_all() -> list[dict]:
    return [fn() for fn in ALL_SYSTEMS]
