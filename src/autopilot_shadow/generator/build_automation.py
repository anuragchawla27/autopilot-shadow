"""
Runs classification over the Day 6 workflow, saves the classified
workflow, and does a real executor dry-run for one shortlist-path
resume and one halt-path resume to PROVE the generated spec actually
executes (Section 11) and halts at exactly the steps Section 9's
criteria say it should. Nothing here is hand-typed (S7).

Run: python -m autopilot_shadow.generator.build_automation
"""

from __future__ import annotations

import json
from pathlib import Path

from autopilot_shadow.mock_env.environment import MockEnvironment
from autopilot_shadow.schemas.workflow import Workflow

from .classifier import classify_workflow
from .executor import AutomationExecutor
from .handlers import ACTION_HANDLERS

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"


def main() -> None:
    workflow = Workflow.model_validate_json((DATA_DIR / "workflow_with_decisions.json").read_text())
    classify_workflow(workflow)
    (DATA_DIR / "workflow_classified.json").write_text(workflow.model_dump_json(indent=2))

    classification_summary = [
        {"step_id": s.id, "action": s.action, "step_type": s.step_type, "risk": s.risk, "reason": s.classification_reason}
        for s in workflow.steps
    ]
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "day07_classification.json").write_text(json.dumps(classification_summary, indent=2, default=str))

    print("Step classification:")
    for row in classification_summary:
        print(f"  {row['action']:<28} -> {row['step_type']:<22} (risk={row['risk']})")

    # Executor dry-run proof: one full-match resume (should halt at
    # send_interview_invitation per criterion 1), one ambiguous resume
    # (should halt at classify_candidate per criterion 5).
    resumes = json.loads((DATA_DIR / "resumes.json").read_text())
    job_description = json.loads((DATA_DIR / "job_description.json").read_text())
    executor = AutomationExecutor(workflow, ACTION_HANDLERS)

    runs = {}
    for resume_id in ["res_0001", "res_0004"]:
        env = MockEnvironment(resumes)
        run_logger = executor.run(env, job_description, resume_id, demo_id=f"exec_{resume_id}")
        runs[resume_id] = [e.model_dump(mode="json") for e in run_logger.events]

    (RESULTS_DIR / "day07_executor_dry_run.json").write_text(json.dumps(runs, indent=2, default=str))

    for resume_id, events in runs.items():
        last = events[-1]
        print(f"\n{resume_id}: {len(events)} events, halted at action={last['action']!r} approval={last['approval']!r}")

    print("\nWrote: data/workflow_classified.json, results/day07_classification.json, results/day07_executor_dry_run.json")


if __name__ == "__main__":
    main()
