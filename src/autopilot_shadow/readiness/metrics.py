"""
Section 27/28 evaluation metrics and Section 29's critical metric — all
computed from real results files prior days already generated. Nothing
here recomputes reconstruction, agreement, or risk from scratch; this
module only reads and aggregates.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"


def reconstruction_accuracy() -> dict:
    """Section 27: 'Can the system recover the correct sequence?' — Day 5's
    own step/edge recall, read directly."""
    d5 = json.loads((RESULTS_DIR / "day05_reconstruction_evaluation.json").read_text())
    return {
        "step_recall": d5["step_recall"],
        "edge_recall": d5["edge_recall"],
        "combined": round((d5["step_recall"] + d5["edge_recall"]) / 2, 4),
    }


def decision_extraction_quality() -> dict:
    """Two DIFFERENT, non-redundant readings of Day 6's extracted rules,
    both honest about how thin the evidence actually is:

    - rule_coverage: of the 6 distinct rules extracted, how many are
      grounded (explicit/inferred) rather than UNKNOWN (single-example
      guesses)? A per-RULE view.
    - evidence_weighted_stability: of all the demonstration EVIDENCE
      behind every rule, how much of it supports a grounded rule? A
      per-OBSERVATION view — weights rule_02's 5 supporting
      demonstrations more than rule_03's lone example, which
      rule_coverage alone would treat identically.
    """
    rules = json.loads((RESULTS_DIR / "day06_decision_extraction.json").read_text())
    grounded_types = {"explicit", "inferred"}

    total_rules = len(rules)
    grounded_rules = sum(1 for r in rules if r["rule_type"] in grounded_types)

    total_evidence = sum(r["evidence_count"] for r in rules)
    grounded_evidence = sum(r["evidence_count"] for r in rules if r["rule_type"] in grounded_types)

    return {
        "total_rules": total_rules,
        "grounded_rules": grounded_rules,
        "rule_coverage": round(grounded_rules / total_rules, 4) if total_rules else None,
        "evidence_weighted_stability": round(grounded_evidence / total_evidence, 4) if total_evidence else None,
    }


def human_ai_agreement() -> dict:
    """Day 9's 5 separate dimensions, plus their plain mean as one
    summary number for the Shadow Score — the mean is ONLY a summary
    convenience; see docs/15 for why it must still be read alongside
    the dimensions, never in place of them (Section 14's own rule)."""
    scores = json.loads((RESULTS_DIR / "day09_agreement_scores.json").read_text())
    dims = {k: v["rate"] for k, v in scores["dimensions"].items()}
    mean = round(sum(dims.values()) / len(dims), 4)
    return {"dimensions": dims, "mean": mean}


def risk_and_reversibility() -> dict:
    """Section 15's categorical Risk/Reversibility fields, rolled up
    across all 7 actions' Day 10 static factors."""
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    from autopilot_shadow.risk.risk_factors import ACTION_RISK_FACTORS, impact_score

    factors = list(ACTION_RISK_FACTORS.values())
    avg_impact = round(sum(impact_score(f) for f in factors) / len(factors), 4)
    reversible_pct = round(100 * sum(1 for f in factors if f.reversible) / len(factors), 1)

    risk_label = "low" if avg_impact < 0.34 else "medium" if avg_impact < 0.67 else "high"
    reversibility_label = "high" if reversible_pct >= 67 else "medium" if reversible_pct >= 34 else "low"

    return {
        "avg_impact_score": avg_impact,
        "risk_label": risk_label,
        "reversible_action_pct": reversible_pct,
        "reversibility_label": reversibility_label,
    }


def false_automation_rate() -> dict:
    """SECTION 29 — THE CRITICAL METRIC. Of every case Day 10 recommended
    'automate', how many would NOT have matched the human's actual
    decision (per Day 9)? This is checked per (resume_id, action) pair
    by cross-referencing Day 10's risk scores against Day 9's per-step
    comparison — not reused from any single prior file, because neither
    Day 9 nor Day 10 alone computed this specific question."""
    risk_scores = json.loads((RESULTS_DIR / "day10_risk_scores.json").read_text())
    comparisons = json.loads((RESULTS_DIR / "day09_comparisons.json").read_text())

    match_by_key: dict[tuple[str, str], bool] = {}
    for comparison in comparisons:
        resume_id = comparison["resume_id"]
        for step in comparison["steps"]:
            if step["match"] is not None:
                match_by_key[(resume_id, step["action"])] = step["match"]

    automate_cases = [s for s in risk_scores if s["recommendation"] == "automate"]
    evaluated = 0
    false_automations = []
    for case in automate_cases:
        key = (case["resume_id"], case["action"])
        matched = match_by_key.get(key)
        if matched is None:
            continue  # no Day 9 comparison data for this case (shouldn't occur in our dataset)
        evaluated += 1
        if not matched:
            false_automations.append(case)

    rate = round(len(false_automations) / evaluated, 4) if evaluated else None
    return {
        "automate_recommendations": len(automate_cases),
        "evaluated_against_human_decision": evaluated,
        "false_automations": false_automations,
        "false_automation_rate": rate,
    }


def false_escalation_rate() -> dict:
    """Section 28's companion metric: of the DISCRETIONARY gated cases
    (automate_with_monitoring — where confidence, not hard policy, drove
    the gate), how many would have matched the human anyway if fully
    automated? `human_review` (structural failures) and
    `approval_required` (Section 22's hard safety override) are
    deliberately excluded — gating those is correct by POLICY regardless
    of whether the AI's guess would have been right, so counting them
    here would misrepresent policy-driven gates as over-caution."""
    risk_scores = json.loads((RESULTS_DIR / "day10_risk_scores.json").read_text())
    comparisons = json.loads((RESULTS_DIR / "day09_comparisons.json").read_text())

    match_by_key: dict[tuple[str, str], bool] = {}
    for comparison in comparisons:
        resume_id = comparison["resume_id"]
        for step in comparison["steps"]:
            if step["match"] is not None:
                match_by_key[(resume_id, step["action"])] = step["match"]

    discretionary = [s for s in risk_scores if s["recommendation"] == "automate_with_monitoring"]
    evaluated = 0
    would_have_matched = []
    for case in discretionary:
        key = (case["resume_id"], case["action"])
        matched = match_by_key.get(key)
        if matched is None:
            continue
        evaluated += 1
        if matched:
            would_have_matched.append(case)

    rate = round(len(would_have_matched) / evaluated, 4) if evaluated else None
    return {
        "discretionary_gated_cases": len(discretionary),
        "evaluated_against_human_decision": evaluated,
        "would_have_matched_if_automated": would_have_matched,
        "false_escalation_rate": rate,
    }
