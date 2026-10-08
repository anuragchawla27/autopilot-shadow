"""
Workflow versioning (Day 12, Section 25).

Section 25's own example progression: "Version 1: Manual -> Version 2:
Partially automated -> Version 3: Human-in-the-loop -> Version 4:
High-confidence automation." This module defines exactly that
progression, but for OUR workflow's actual history, with every metric
pulled from a real results file this project already generated — none
hand-typed (S7).

HOW EACH VERSION MAPS TO WHAT WE ACTUALLY BUILT:
- V1 MANUAL   -- Day 4's human demonstrations: no AI involved at all.
- V2 AI-PROPOSED (SHADOW) -- Day 8: the AI proposes an action for every
  step, but nothing is risk-scored or gated yet — "partially automated"
  in the sense that proposals exist, not that anything executes.
- V3 RISK-AWARE HUMAN-IN-THE-LOOP -- Day 10 + Day 11: every proposal
  now has a risk score and a recommendation, gated by Section 18's
  explicit approval mechanism.
- V4 HIGH-CONFIDENCE AUTOMATION -- NOT YET REACHED. Honestly marked
  `reached=False` rather than invented. Section 26 (Day 13) is where
  this project will actually decide whether the evidence supports
  calling any step "ready" for this tier — V4 is defined here as a
  placeholder target, not claimed as already achieved.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"


@dataclass(frozen=True)
class WorkflowVersion:
    version: int
    label: str
    description: str
    built_in_day: int
    reached: bool
    metrics: dict

    def as_dict(self) -> dict:
        return {
            "version": self.version,
            "label": self.label,
            "description": self.description,
            "built_in_day": self.built_in_day,
            "reached": self.reached,
            "metrics": self.metrics,
        }


def _human_step_counts() -> dict:
    demos = json.loads((DATA_DIR / "demonstrations.json").read_text())
    plain = [e for e in demos if e["demo_id"].startswith("demo_0")]
    resumes = {e["demo_id"] for e in plain}
    return {"resumes": len(resumes), "total_events": len(plain)}


def _shadow_step_counts() -> dict:
    shadow = json.loads((DATA_DIR / "shadow_run.json").read_text())
    return {"resumes": len({e["demo_id"] for e in shadow}), "total_proposed_events": len(shadow)}


def _risk_distribution() -> dict:
    scores = json.loads((RESULTS_DIR / "day10_risk_scores.json").read_text())
    from collections import Counter

    counts = Counter(s["recommendation"] for s in scores)
    return {"total_scored": len(scores), "by_recommendation": dict(counts)}


def _agreement_summary() -> dict:
    scores = json.loads((RESULTS_DIR / "day09_agreement_scores.json").read_text())
    return {dim: d["rate"] for dim, d in scores["dimensions"].items()}


def build_versions() -> list[WorkflowVersion]:
    human = _human_step_counts()
    shadow = _shadow_step_counts()
    risk = _risk_distribution()
    agreement = _agreement_summary()

    v1 = WorkflowVersion(
        version=1,
        label="Manual",
        description="Human-only resume screening (Day 4). No AI involvement at any step.",
        built_in_day=4,
        reached=True,
        metrics={"automation_coverage_pct": 0.0, "human_events": human["total_events"], "resumes": human["resumes"]},
    )
    v2 = WorkflowVersion(
        version=2,
        label="AI-Proposed (Shadow)",
        description="AI generates a proposed action for every step via shadow execution (Day 7-8), but "
        "nothing is risk-scored, gated, or ever actually executed.",
        built_in_day=8,
        reached=True,
        metrics={
            "automation_coverage_pct": 0.0,  # shadow mode never executes for real
            "ai_proposals": shadow["total_proposed_events"],
            "resumes": shadow["resumes"],
            "historical_agreement": agreement,  # Day 9 — see D-043 honest caveat before citing this
        },
    )
    v3 = WorkflowVersion(
        version=3,
        label="Risk-Aware Human-in-the-Loop",
        description="Every AI proposal now carries a Day 10 risk score/recommendation and passes through "
        "Day 11's explicit 4-state approval gate before anything could execute.",
        built_in_day=11,
        reached=True,
        metrics={
            "automation_coverage_pct": round(
                100 * risk["by_recommendation"].get("automate", 0) / risk["total_scored"], 1
            ),
            "gated_pct": round(
                100 * (risk["total_scored"] - risk["by_recommendation"].get("automate", 0)) / risk["total_scored"], 1
            ),
            "risk_distribution": risk["by_recommendation"],
        },
    )
    v4 = WorkflowVersion(
        version=4,
        label="High-Confidence Automation",
        description="Target tier: steps with strong, evidenced agreement and low risk execute without a "
        "human gate. NOT YET REACHED — Day 13's readiness assessment (Section 26) is where this project "
        "will decide, from real evidence, whether any step actually qualifies. Nothing here claims it does.",
        built_in_day=13,
        reached=False,
        metrics={},
    )
    return [v1, v2, v3, v4]
