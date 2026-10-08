"""
Disagreement investigation records (Day 11, Section 16).

Section 16's own example shape:

    AI-HUMAN DISAGREEMENT RECORD
    Workflow: Resume Screening | Step: Candidate Evaluation
    Human decision: Human Review | AI decision: Reject
    AI confidence: 81%
    Available evidence: 2/4 required skills
    Potential reason: Skill synonym interpretation
    Risk: High
    Recommended action: Human review

This module builds exactly that record, but from REAL data already
computed by prior days rather than inventing new analysis:
- Human decision / AI decision / confidence / evidence come straight
  from Day 9's `comparison/engine.py` per-step comparison (`human_value`,
  `ai_value`, `ai_confidence`) — no new extraction logic.
- Risk comes straight from Day 10's `risk/risk_model.py` score for that
  exact (resume_id, action) pair — never recomputed here.
- `recommended_action` is Day 10's own `recommendation` field, reused
  verbatim — this module does not invent a second, possibly
  inconsistent, notion of what should happen next.

The one genuinely new piece is `potential_reason`: a short, HONEST,
RULE-BASED guess (not a model call, not invented insight) at why the
two sides might differ, grounded only in what the comparison record
already shows (which dimension actually disagreed). Section 16 asks for
"potential reason," not a certified root cause, and the brief's own
example ("Skill synonym interpretation") is exactly this kind of
plausible, evidence-grounded guess — not a proven explanation.

HARD RULE (Section 16's own words): "The system should never silently
overwrite the human decision." This module only ever PRODUCES AN
INVESTIGATION RECORD — nothing here writes to the human's own data, and
no function in this module can change `human_value`. Enforced
structurally: these functions take a comparison dict and return a new
dict; they have no access to, and never call, anything in
`logger/human_demo.py` or the mock environment's write methods.
"""

from __future__ import annotations

from typing import Optional


def _guess_reason(step: dict) -> str:
    """A short, rule-based guess at why human and AI differ on this
    step, grounded only in which part of the step comparison actually
    disagreed. Never claims certainty."""
    if step.get("tool_agreement") is False:
        return "Different tool/application used for this step — a data-source mismatch, not a judgment one."
    if step.get("is_data_step"):
        return "Extracted data differs between human and AI — likely a parsing or source-data difference."
    if step.get("is_decision_step"):
        return (
            "Same step, different outcome recorded — likely a borderline case near the decision "
            "boundary (e.g. a skill/experience value close to the policy threshold)."
        )
    if step.get("human_present") != step.get("ai_present"):
        return "One side recorded this step and the other did not — a workflow-path difference, not necessarily a judgment one."
    return "Outputs differ for this step; no specific dimension stands out as the cause."


def build_disagreement_records(
    comparison: dict,
    risk_scores_by_key: dict[tuple[str, str], dict],
    workflow_name: str = "resume_screening",
) -> list[dict]:
    """Builds one Section-16 record per step where Day 9 found a
    mismatch for this resume. `risk_scores_by_key` maps
    (resume_id, action) -> that case's Day 10 risk_model.score_case()
    output (as_dict()).
    """
    resume_id = comparison["resume_id"]
    records = []
    for step in comparison["steps"]:
        if step["match"] is not False:  # only real mismatches (True/None are not disagreements)
            continue

        action = step["action"]
        risk = risk_scores_by_key.get((resume_id, action))

        records.append(
            {
                "workflow": workflow_name,
                "resume_id": resume_id,
                "step": action,
                "human_decision": step["human_value"],
                "ai_decision": step["ai_value"],
                "ai_confidence": step.get("ai_confidence"),
                "evidence": {
                    "human_present": step["human_present"],
                    "ai_present": step["ai_present"],
                    "human_value": step["human_value"],
                    "ai_value": step["ai_value"],
                },
                "potential_reason": _guess_reason(step),
                "risk_score": risk["risk_score"] if risk else None,
                "recommended_action": risk["recommendation"] if risk else "human_review",
                "risk_reason": risk["reason"] if risk else "No Day 10 risk score available for this step.",
            }
        )
    return records


def build_all_disagreement_records(
    comparisons: list[dict],
    risk_scores: list[dict],
    workflow_name: str = "resume_screening",
) -> list[dict]:
    risk_scores_by_key = {(s["resume_id"], s["action"]): s for s in risk_scores if s.get("resume_id")}
    all_records = []
    for comparison in comparisons:
        all_records.extend(build_disagreement_records(comparison, risk_scores_by_key, workflow_name))
    return all_records
