"""
Runs the comparison engine over the real Day 4 human demonstrations and
Day 8 AI shadow run, writes the full per-resume comparison table and the
dataset-level 5-dimension agreement scores. Nothing hand-typed (S7).

Run: python -m autopilot_shadow.comparison.build_comparison
"""

from __future__ import annotations

import json
from pathlib import Path

from .agreement import score_dataset
from .engine import compare_all

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"


def main() -> None:
    human_events = json.loads((DATA_DIR / "demonstrations.json").read_text())
    ai_events = json.loads((DATA_DIR / "shadow_run.json").read_text())

    comparisons = compare_all(human_events, ai_events)
    scores = score_dataset(comparisons)

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "day09_comparisons.json").write_text(json.dumps(comparisons, indent=2, default=str))
    (RESULTS_DIR / "day09_agreement_scores.json").write_text(json.dumps(scores, indent=2, default=str))

    print(f"Compared {scores['num_resumes_compared']} resumes.")
    print("Agreement dimensions (separate, not combined):")
    for dim, d in scores["dimensions"].items():
        print(f"  {dim:<20} {d['matched']}/{d['evaluable']}  rate={d['rate']}")
    print(f"\nOutcome disagreements: {len(scores['outcome_disagreements'])}")
    for d in scores["outcome_disagreements"]:
        print(f"  {d['resume_id']}: human={d['human_final_classification']!r} vs ai={d['ai_final_classification']!r}")

    print("\nWrote: results/day09_comparisons.json, results/day09_agreement_scores.json")


if __name__ == "__main__":
    main()
