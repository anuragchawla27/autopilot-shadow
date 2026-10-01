"""
Runs decision extraction over the real dataset, attaches the resulting
Rules to the `classify_candidate` step of Day 5's reconstructed
workflow, and writes both the annotated workflow and a plain summary
table to disk (S7 — nothing here is hand-typed).

Scope note: this does NOT create a new workflow VERSION (Section 25 —
that's Day 12's job). It's the same structural workflow from Day 5,
now with its decision rules filled in, saved separately so Day 5's
original output stays untouched.

Run: python -m autopilot_shadow.decisions.build_rules
"""

from __future__ import annotations

import json
from pathlib import Path

from autopilot_shadow.schemas.workflow import Workflow

from .extraction import load_and_extract

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"


def main() -> None:
    rules = load_and_extract(DATA_DIR)

    workflow = Workflow.model_validate_json((DATA_DIR / "reconstructed_workflow_v1.json").read_text())
    classify_step = next(s for s in workflow.steps if s.action == "classify_candidate")
    classify_step.rules = rules

    (DATA_DIR / "workflow_with_decisions.json").write_text(workflow.model_dump_json(indent=2))

    summary = [
        {
            "rule_id": r.rule_id,
            "rule_type": r.rule_type.value,
            "then_outcome": r.then_outcome,
            "evidence_count": r.evidence_count,
            "source_demo_ids": r.source_demo_ids,
            "description": r.description,
        }
        for r in rules
    ]
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "day06_decision_extraction.json").write_text(json.dumps(summary, indent=2, default=str))

    counts = {"explicit": 0, "inferred": 0, "unknown": 0}
    for r in rules:
        counts[r.rule_type.value] += 1

    print(f"Extracted {len(rules)} rules: {counts}")
    for r in rules:
        print(f"  [{r.rule_type.value:>8}] (n={r.evidence_count}) {r.description}")
    print("Wrote: data/workflow_with_decisions.json, results/day06_decision_extraction.json")


if __name__ == "__main__":
    main()
