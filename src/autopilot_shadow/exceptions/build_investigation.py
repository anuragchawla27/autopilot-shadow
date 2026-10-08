"""
Runs Day 11's three pieces over the real data from Days 8-10 and writes
the results — nothing hand-typed (S7).

Run: python -m autopilot_shadow.exceptions.build_investigation
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .approval_gate import build_approval_queue
from .detector import detect_all
from .disagreement import build_all_disagreement_records

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"


def main() -> None:
    shadow_events = json.loads((DATA_DIR / "shadow_run.json").read_text())
    comparisons = json.loads((RESULTS_DIR / "day09_comparisons.json").read_text())
    risk_scores = json.loads((RESULTS_DIR / "day10_risk_scores.json").read_text())

    # Section 17 — exception detection
    exceptions = detect_all(shadow_events)
    exception_dicts = [asdict(e) for e in exceptions]

    # Section 16 — disagreement investigation
    disagreements = build_all_disagreement_records(comparisons, risk_scores)

    # Section 18 — approval queue (PENDING only; nothing here resolves a decision)
    queue = build_approval_queue(risk_scores)
    queue_dicts = [asdict(q) for q in queue]

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "day11_exceptions.json").write_text(json.dumps(exception_dicts, indent=2, default=str))
    (RESULTS_DIR / "day11_disagreements.json").write_text(json.dumps(disagreements, indent=2, default=str))
    (RESULTS_DIR / "day11_approval_queue.json").write_text(json.dumps(queue_dicts, indent=2, default=str))

    print(f"Exceptions detected: {len(exception_dicts)} / {len(shadow_events)} AI-proposed events")
    for e in exception_dicts:
        print(f"  {e['demo_id']:<18} {e['action']:<26} trigger={e['trigger']:<22} -> {e['reason']}")

    print(f"\nDisagreement records: {len(disagreements)} (Day 9 found 0 real mismatches — see docs/13 for why)")

    print(f"\nApproval queue: {len(queue_dicts)} / {len(risk_scores)} proposed actions need a gate")
    from collections import Counter

    counts = Counter(q["recommendation"] for q in queue_dicts)
    for rec, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {rec:<24} {n}")

    print(
        "\nWrote: results/day11_exceptions.json, results/day11_disagreements.json, "
        "results/day11_approval_queue.json"
    )


if __name__ == "__main__":
    main()
