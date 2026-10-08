"""
Runs Day 13's full automation-readiness evaluation over real data from
every prior day and writes the results — nothing hand-typed (S7).

Run: python -m autopilot_shadow.readiness.build_readiness
"""

from __future__ import annotations

import json
from pathlib import Path

from .readiness_decision import decide_readiness
from .shadow_score import compute_shadow_score

ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = ROOT / "results"

GATES_OPERATIONAL = True  # Day 11 built and tested the approval gate mechanism


def main() -> None:
    score = compute_shadow_score()
    decision = decide_readiness(
        evidence_coverage=score["decision_extraction_quality"]["rule_coverage"],
        false_automation_rate=score["false_automation_rate"]["false_automation_rate"],
        gates_operational=GATES_OPERATIONAL,
    )

    result = {
        "shadow_score": score,
        "readiness_decision": {"tier": decision.tier, "reason": decision.reason},
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "day13_readiness_assessment.json").write_text(json.dumps(result, indent=2, default=str))

    print(f"SHADOW SCORE: {score['shadow_score']} / 100", end="")
    if score["hard_capped_by_false_automation"]:
        print(f"  (capped from {score['raw_score_before_cap']} — false automation observed)")
    else:
        print()

    print("\nDecomposed (Section 15 — never read the headline number alone):")
    for name, value in score["components"].items():
        print(f"  {name:<22} {value}")
    print(f"  {'risk':<22} {score['risk']}")
    print(f"  {'reversibility':<22} {score['reversibility']}")

    print(f"\nSection 29 — CRITICAL METRIC — false_automation_rate: "
          f"{score['false_automation_rate']['false_automation_rate']} "
          f"({len(score['false_automation_rate']['false_automations'])} / "
          f"{score['false_automation_rate']['evaluated_against_human_decision']} automate cases)")
    print(f"Companion — false_escalation_rate (discretionary gates only): "
          f"{score['false_escalation_rate']['false_escalation_rate']} "
          f"({len(score['false_escalation_rate']['would_have_matched_if_automated'])} / "
          f"{score['false_escalation_rate']['evaluated_against_human_decision']} monitored cases)")

    print(f"\nREADINESS DECISION (Section 26): {decision.tier}")
    print(f"  {decision.reason}")

    print("\nWrote: results/day13_readiness_assessment.json")


if __name__ == "__main__":
    main()
