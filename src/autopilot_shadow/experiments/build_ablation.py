"""
Day 15 — runs Ablation Systems A-E (Section 31) and writes the real
result to `results/day15_ablation.json` (S7).

Run: python -m autopilot_shadow.experiments.build_ablation
"""

from __future__ import annotations

import json
from pathlib import Path

from .ablation_engine import run_all

RESULTS_DIR = Path(__file__).resolve().parents[3] / "results"


def build() -> list[dict]:
    results = run_all()
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "day15_ablation.json").write_text(json.dumps(results, indent=2, default=str))
    return results


if __name__ == "__main__":
    results = build()
    print(f"{'Sys':<4}{'Name':<34}{'Coverage':>10}{'Errors':>8}{'FalseAuto':>11}{'UnsafeSend':>12}{'AvgSteps':>10}")
    for r in results:
        m = r["metrics"]
        print(
            f"{r['system']:<4}{r['name']:<34}{m['automation_coverage_pct']:>9}%"
            f"{m['errors']:>8}{m['false_automation']:>11}{m['unsafe_invitations_sent']:>12}"
            f"{m['avg_steps_executed']:>10}"
        )
    print("\nWrote: results/day15_ablation.json")
