"""
Runs the reconstruction engine over the real Day 4 dataset and writes
both the reconstructed Workflow and its evaluation-against-Section-5
result to disk, so nothing in docs/07 is hand-typed (S7).

Run: python -m autopilot_shadow.reconstruction.build_workflow
"""

from __future__ import annotations

import json
from pathlib import Path

from .engine import filter_structural_demos, reconstruct_workflow, reconstruction_stats
from .evaluate import evaluate_reconstruction

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"


def main() -> None:
    events = json.loads((DATA_DIR / "demonstrations.json").read_text())
    structural_events = filter_structural_demos(events)

    workflow = reconstruct_workflow(structural_events, workflow_name="resume_screening", workflow_id="wf_resume_screening_v1")
    stats = reconstruction_stats(workflow, structural_events)
    evaluation = evaluate_reconstruction(workflow)

    RESULTS_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "reconstructed_workflow_v1.json").write_text(workflow.model_dump_json(indent=2))
    (RESULTS_DIR / "day05_reconstruction_stats.json").write_text(json.dumps(stats, indent=2))
    (RESULTS_DIR / "day05_reconstruction_evaluation.json").write_text(json.dumps(evaluation, indent=2, default=str))

    print(f"Reconstructed workflow: {stats['num_distinct_steps']} steps from {stats['num_demonstrations']} demonstrations")
    print(f"Step recall vs Section 5 sequence: {evaluation['step_recall']*100:.1f}%")
    print(f"Edge recall vs Section 5 sequence: {evaluation['edge_recall']*100:.1f}%")
    print(f"Wrote: data/reconstructed_workflow_v1.json, results/day05_reconstruction_stats.json, results/day05_reconstruction_evaluation.json")


if __name__ == "__main__":
    main()
