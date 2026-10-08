"""
Runs the Day 10 risk model over the real Day 8 shadow run (74 AI-proposed
events) and the real Day 9 comparisons (for per-action historical
agreement), and writes actual generated risk scores — never hand-typed
(S7), unlike Section 10's own illustrative example table.

Run: python -m autopilot_shadow.risk.build_risk_scores
"""

from __future__ import annotations

import json
from pathlib import Path

from .historical_agreement import per_action_agreement
from .risk_model import score_case

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"


def main() -> None:
    shadow_events = json.loads((DATA_DIR / "shadow_run.json").read_text())
    comparisons = json.loads((RESULTS_DIR / "day09_comparisons.json").read_text())

    agreement_by_action = per_action_agreement(comparisons)

    scores = []
    for evt in shadow_events:
        action = evt["action"]
        resume_id = evt["demo_id"].replace("shadow_", "")
        agreement = agreement_by_action.get(action, {}).get("rate")
        score = score_case(
            action=action,
            resume_id=resume_id,
            confidence=evt.get("confidence"),
            result=evt["result"],
            historical_agreement_rate=agreement,
        )
        scores.append(score.as_dict())

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "day10_risk_scores.json").write_text(json.dumps(scores, indent=2, default=str))
    (RESULTS_DIR / "day10_historical_agreement_by_action.json").write_text(
        json.dumps(agreement_by_action, indent=2, default=str)
    )

    print(f"Scored {len(scores)} AI-proposed actions across {len(shadow_events)} shadow events.\n")
    print(f"{'ACTION':<28} {'RESUME':<10} {'CONF':>6} {'RISK':>6}  RECOMMENDATION")
    for s in scores:
        conf = f"{s['confidence']:.2f}" if s["confidence"] is not None else "  n/a"
        print(f"{s['action']:<28} {s['resume_id']:<10} {conf:>6} {s['risk_score']:>6.2f}  {s['recommendation']}")

    print("\nRecommendation counts:")
    from collections import Counter

    counts = Counter(s["recommendation"] for s in scores)
    for rec, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {rec:<24} {n}")

    print("\nWrote: results/day10_risk_scores.json, results/day10_historical_agreement_by_action.json")


if __name__ == "__main__":
    main()
