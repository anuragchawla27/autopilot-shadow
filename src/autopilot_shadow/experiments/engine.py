"""
Day 15 — Experiments A-E (Section 30), run over the real 12-resume
dataset. Each experiment is a different executor/policy; all 5 are
reduced to the same `CaseOutcome` shape (`case_outcome.py`) so they can
be compared on Section 30's own metrics: automation coverage, errors,
human interventions, latency, false automation, workflow completion.

  A — Manual workflow baseline        (data/demonstrations.json, Day 4)
  B — AI-generated workflow           (NaiveExecutor — no gates at all)
  C — AI workflow + human approval    (AutomationExecutor — Day 7, real)
  D — AI workflow + confidence threshold (ConfidenceOnlyExecutor)
  E — AI workflow + risk-aware automation (RiskAwareExecutor — Day 10+11, real)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from autopilot_shadow.generator.executor import AutomationExecutor
from autopilot_shadow.generator.handlers import ACTION_HANDLERS
from autopilot_shadow.mock_env.environment import MockEnvironment
from autopilot_shadow.reconstruction.engine import filter_structural_demos
from autopilot_shadow.schemas.event import Event
from autopilot_shadow.schemas.workflow import Workflow

from .case_outcome import CaseOutcome, aggregate
from .confidence_only_executor import ConfidenceOnlyExecutor
from .naive_executor import NaiveExecutor
from .risk_aware_executor import RiskAwareExecutor

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"

RESUME_IDS = [f"res_{i:04d}" for i in range(1, 13)]


def _load_json(path: Path):
    return json.loads(path.read_text())


def _resumes() -> list[dict]:
    return _load_json(DATA_DIR / "resumes.json")


def _job_description() -> dict:
    return _load_json(DATA_DIR / "job_description.json")


def _ground_truth() -> dict:
    return _load_json(DATA_DIR / "ground_truth.json")["labels"]


def _classified_workflow() -> Workflow:
    return Workflow.model_validate_json((DATA_DIR / "workflow_classified.json").read_text())


def _outcome_from_events(
    resume_id: str,
    expected_decision: str,
    events: list[Event],
    automated: bool,
    halted_for_human: bool,
) -> CaseOutcome:
    failed = any(e.result == "failure" for e in events)
    final_action = None
    for e in events:
        if e.action == "classify_candidate" and e.decision is not None:
            final_action = e.decision.outcome
    would_send = any(
        e.action == "send_interview_invitation" and e.result == "success" and e.output.get("would_send", True)
        for e in events
    )
    matches = (final_action == expected_decision) if final_action is not None else None
    return CaseOutcome(
        resume_id=resume_id,
        expected_decision=expected_decision,
        final_action=final_action,
        automated=automated and not failed,
        halted_for_human=halted_for_human,
        failed=failed,
        would_send_invitation=would_send,
        steps_executed=len(events),
        matches_ground_truth=matches,
    )


# --- Experiment A: Manual workflow baseline -------------------------------
def run_experiment_a() -> dict:
    demos = _load_json(DATA_DIR / "demonstrations.json")
    structural = filter_structural_demos(demos)
    ground_truth = _ground_truth()

    by_demo: dict[str, list[dict]] = {}
    for e in structural:
        by_demo.setdefault(e["demo_id"], []).append(e)

    outcomes = []
    for resume_id in RESUME_IDS:
        demo_events = next(
            (evts for evts in by_demo.values() if evts and evts[0]["input"].get("resume_id") == resume_id),
            None,
        )
        if demo_events is None:
            continue
        failed = any(e["result"] == "failure" for e in demo_events)
        final_action = None
        for e in demo_events:
            if e["action"] == "classify_candidate" and e.get("decision"):
                final_action = e["decision"]["outcome"]
        would_send = any(e["action"] == "send_interview_invitation" and e["result"] == "success" for e in demo_events)
        expected = ground_truth[resume_id]["expected_decision"]
        matches = (final_action == expected) if final_action is not None else None
        outcomes.append(
            CaseOutcome(
                resume_id=resume_id,
                expected_decision=expected,
                final_action=final_action,
                automated=False,  # a human did every case, start to finish
                halted_for_human=True,  # every case required full human handling
                failed=failed,
                would_send_invitation=would_send,
                steps_executed=len(demo_events),
                matches_ground_truth=matches,
            )
        )

    return {
        "experiment": "A",
        "name": "Manual workflow baseline",
        "description": "The human demo policy (Day 4) performing every step itself, no AI involvement.",
        "cases": [o.as_dict() for o in outcomes],
        "metrics": aggregate(outcomes),
    }


def _run_generic_experiment(experiment_id: str, name: str, description: str, run_fn) -> dict:
    resumes = _resumes()
    job_description = _job_description()
    ground_truth = _ground_truth()
    outcomes = []
    for resume_id in RESUME_IDS:
        env = MockEnvironment(resumes)  # fresh env per case, same reasoning as Day 8's shadow engine
        logger = run_fn(env, job_description, resume_id)
        expected = ground_truth[resume_id]["expected_decision"]
        last_event = logger.events[-1] if logger.events else None
        # Event.approval uses use_enum_values=True (schemas/event.py), so this
        # is already a plain string at runtime, not an ApprovalState member.
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
    return {
        "experiment": experiment_id,
        "name": name,
        "description": description,
        "cases": [o.as_dict() for o in outcomes],
        "metrics": aggregate(outcomes),
    }


# --- Experiment B: AI-generated workflow, no gates ------------------------
def run_experiment_b() -> dict:
    workflow = _classified_workflow()

    def _run(env, jd, resume_id):
        return NaiveExecutor(workflow).run(env, jd, resume_id, demo_id=f"expB_{resume_id}")

    return _run_generic_experiment(
        "B",
        "AI-generated workflow",
        "Every step executed automatically with NO safety gates — the unsafe baseline Section 1 warns about.",
        _run,
    )


# --- Experiment C: AI workflow + human approval ---------------------------
def run_experiment_c() -> dict:
    workflow = _classified_workflow()

    def _run(env, jd, resume_id):
        return AutomationExecutor(workflow, ACTION_HANDLERS).run(env, jd, resume_id, demo_id=f"expC_{resume_id}")

    return _run_generic_experiment(
        "C",
        "AI workflow + human approval",
        "Day 7's real AutomationExecutor: halts at any step classified human_review/human_only/blocked.",
        _run,
    )


# --- Experiment D: AI workflow + confidence threshold ----------------------
def run_experiment_d() -> dict:
    workflow = _classified_workflow()

    def _run(env, jd, resume_id):
        return ConfidenceOnlyExecutor(workflow).run(env, jd, resume_id, demo_id=f"expD_{resume_id}")

    return _run_generic_experiment(
        "D",
        "AI workflow + confidence threshold",
        "Gates purely on Section 21's confidence thresholds (>90% automate, <70% review) — no risk model.",
        _run,
    )


# --- Experiment E: AI workflow + risk-aware automation ----------------------
def run_experiment_e() -> dict:
    workflow = _classified_workflow()
    historical_agreement = _load_json(RESULTS_DIR / "day10_historical_agreement_by_action.json")

    def _run(env, jd, resume_id):
        return RiskAwareExecutor(workflow, historical_agreement).run(env, jd, resume_id, demo_id=f"expE_{resume_id}")

    return _run_generic_experiment(
        "E",
        "AI workflow + risk-aware automation",
        "The project's complete real decision chain: Day 10's risk model + Day 11's gate logic, case by case.",
        _run,
    )


ALL_EXPERIMENTS = [run_experiment_a, run_experiment_b, run_experiment_c, run_experiment_d, run_experiment_e]


def run_all() -> list[dict]:
    return [fn() for fn in ALL_EXPERIMENTS]
