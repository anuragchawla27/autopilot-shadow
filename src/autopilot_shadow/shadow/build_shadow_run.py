"""
Runs shadow execution over all 12 synthetic resumes, producing the
AI-proposed Events that Day 9's comparison engine will read. Nothing
hand-typed (S7) — this is real output from the real executor.

Run: python -m autopilot_shadow.shadow.build_shadow_run
"""

from __future__ import annotations

import json
from pathlib import Path

from autopilot_shadow.schemas.workflow import Workflow

from .shadow_executor import ShadowExecutor

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"


def main() -> None:
    workflow = Workflow.model_validate_json((DATA_DIR / "workflow_classified.json").read_text())
    resumes = json.loads((DATA_DIR / "resumes.json").read_text())
    job_description = json.loads((DATA_DIR / "job_description.json").read_text())

    executor = ShadowExecutor(workflow)
    all_events: list[dict] = []
    resume_ids = [r["resume_id"] for r in resumes]

    for resume_id in resume_ids:
        run_logger = executor.run(resumes, job_description, resume_id, demo_id=f"shadow_{resume_id}")
        all_events.extend(e.model_dump(mode="json") for e in run_logger.events)

    (DATA_DIR / "shadow_run.json").write_text(json.dumps(all_events, indent=2, default=str))

    # Summary: did every resume at least get through classify_candidate?
    summary = []
    for resume_id in resume_ids:
        demo_events = [e for e in all_events if e["demo_id"] == f"shadow_{resume_id}"]
        last = demo_events[-1] if demo_events else None
        proposed_classification = next(
            (e["decision"]["outcome"] for e in demo_events if e["action"] == "classify_candidate" and e.get("decision")),
            None,
        )
        confidence = next(
            (e["confidence"] for e in demo_events if e["action"] == "classify_candidate"),
            None,
        )
        summary.append(
            {
                "resume_id": resume_id,
                "num_events": len(demo_events),
                "last_action": last["action"] if last else None,
                "last_result": last["result"] if last else None,
                "ai_proposed_classification": proposed_classification,
                "ai_confidence": confidence,
            }
        )

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "day08_shadow_run_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    print(f"Shadow-executed {len(resume_ids)} resumes, {len(all_events)} total proposed events.")
    for row in summary:
        print(
            f"  {row['resume_id']}: {row['num_events']} events, last={row['last_action']!r} "
            f"({row['last_result']}), proposed={row['ai_proposed_classification']!r}, "
            f"confidence={row['ai_confidence']}"
        )
    print("\nWrote: data/shadow_run.json, results/day08_shadow_run_summary.json")


if __name__ == "__main__":
    main()
