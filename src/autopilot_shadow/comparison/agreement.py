"""
Human-AI agreement scoring (Day 9, Section 14).

"Create a measurable agreement system based on multiple dimensions:
ACTION AGREEMENT, DATA AGREEMENT, DECISION AGREEMENT, TOOL AGREEMENT,
OUTCOME AGREEMENT. Do not reduce everything to one number without
preserving the underlying dimensions."

This module computes each dimension SEPARATELY, per resume and across
the whole dataset, and never combines them into a single score. Day 13's
readiness assessment is the only place a combined number may appear, and
even there it must stay decomposable (Section 15) — this module's job is
only to measure, not to summarize into one verdict.

DIMENSION DEFINITIONS (our own design, grounded in Section 14's names):
- ACTION AGREEMENT: did the AI reach/propose the same step the human
  took, with an equivalent effect (accounting for the documented
  no-op-vs-not-logged asymmetry — see comparison/engine.py)?
- DATA AGREEMENT: for pure extraction steps (fetch_resume,
  extract_resume), did the AI extract the same information?
- DECISION AGREEMENT: for judgment steps with a DecisionRecord
  (check_experience, compare_skills, classify_candidate), did the AI
  reach the same outcome?
- TOOL AGREEMENT: did the AI use the same application/tool for a step
  both sides actually took?
- OUTCOME AGREEMENT: computed ONCE per resume (not per step) — did the
  end-to-end result match (final classification AND whether a real vs.
  proposed email occurred)?
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DimensionScore:
    matched: int
    evaluable: int

    @property
    def rate(self) -> float | None:
        if self.evaluable == 0:
            return None  # no evaluable cases - explicitly distinct from a 0% agreement rate
        return round(self.matched / self.evaluable, 4)

    def as_dict(self) -> dict:
        return {"matched": self.matched, "evaluable": self.evaluable, "rate": self.rate}


def score_resume(comparison: dict) -> dict:
    """Per-resume agreement across the 5 dimensions, kept separate."""
    steps = comparison["steps"]

    action = DimensionScore(0, 0)
    data = DimensionScore(0, 0)
    decision = DimensionScore(0, 0)
    tool = DimensionScore(0, 0)

    for step in steps:
        if step["match"] is not None:
            action.evaluable += 1
            if step["match"]:
                action.matched += 1

        if step["is_data_step"] and step["human_present"] and step["ai_present"]:
            data.evaluable += 1
            if step["match"]:
                data.matched += 1

        if step["is_decision_step"] and step["human_present"] and step["ai_present"]:
            decision.evaluable += 1
            if step["match"]:
                decision.matched += 1

        if step["tool_agreement"] is not None:
            tool.evaluable += 1
            if step["tool_agreement"]:
                tool.matched += 1

    outcome = DimensionScore(1 if comparison["outcome_agreement"] else 0, 1)

    return {
        "resume_id": comparison["resume_id"],
        "action_agreement": action.as_dict(),
        "data_agreement": data.as_dict(),
        "decision_agreement": decision.as_dict(),
        "tool_agreement": tool.as_dict(),
        "outcome_agreement": outcome.as_dict(),
    }


def score_dataset(comparisons: list[dict]) -> dict:
    """Dataset-level rollup — still 5 SEPARATE numbers, never merged."""
    per_resume_scores = [score_resume(c) for c in comparisons]

    totals = {
        "action_agreement": DimensionScore(0, 0),
        "data_agreement": DimensionScore(0, 0),
        "decision_agreement": DimensionScore(0, 0),
        "tool_agreement": DimensionScore(0, 0),
        "outcome_agreement": DimensionScore(0, 0),
    }
    for res_score in per_resume_scores:
        for dim in totals:
            totals[dim].matched += res_score[dim]["matched"]
            totals[dim].evaluable += res_score[dim]["evaluable"]

    disagreements = [
        {
            "resume_id": c["resume_id"],
            "human_final_classification": c["human_final_classification"],
            "ai_final_classification": c["ai_final_classification"],
        }
        for c in comparisons
        if not c["outcome_agreement"]
    ]

    return {
        "num_resumes_compared": len(comparisons),
        "dimensions": {dim: score.as_dict() for dim, score in totals.items()},
        "per_resume": per_resume_scores,
        "outcome_disagreements": disagreements,
    }
