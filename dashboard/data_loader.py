"""
Dashboard data loading (Day 14, Section 32).

Deliberately pure, Streamlit-free functions: every function here takes
a results/data directory and returns plain Python (dicts/lists) read
straight from a prior day's real JSON output. This is the same split
the rest of the project already uses (a `build_*.py` script computes,
a separate module presents) — it means these functions are directly
unit-testable without importing Streamlit at all, and the dashboard
itself (`app.py`) never recomputes a number a prior day already
produced; it only reads and displays.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def load_workflow_structure() -> dict | None:
    """Section 32: 'Current workflow structure.' Reads the Day 7
    classified workflow (step types, risk, rules) — the most complete
    structural representation the project has produced."""
    return _read_json(DATA_DIR / "workflow_classified.json")


def load_shadow_run() -> list[dict]:
    """Section 32: 'AI-proposed actions (Shadow Execution).' Day 8's
    full shadow event log, one row per proposed action."""
    return _read_json(DATA_DIR / "shadow_run.json") or []


def load_comparisons() -> list[dict]:
    """Section 32: 'Human vs AI comparison.' Day 9's per-resume,
    per-step comparison records (5 agreement dimensions, Section 14)."""
    return _read_json(RESULTS_DIR / "day09_comparisons.json") or []


def load_agreement_scores() -> dict | None:
    """Day 9's aggregated agreement scores (summary of the above)."""
    return _read_json(RESULTS_DIR / "day09_agreement_scores.json")


def load_disagreements() -> list[dict]:
    """Section 32: 'Disagreements.' Day 11's investigation records.
    Real count is 0 (D-054's honest same-author finding) — the
    dashboard must show that plainly, not hide an empty state."""
    return _read_json(RESULTS_DIR / "day11_disagreements.json") or []


def load_readiness() -> dict | None:
    """Section 32: 'Current automation readiness.' Day 13's Shadow
    Score, its decomposition, and the readiness-tier decision — read
    directly, never recomputed here (Day 13's own instruction for
    Day 14)."""
    return _read_json(RESULTS_DIR / "day13_readiness_assessment.json")


def load_risk_scores() -> list[dict]:
    """Section 32: 'Risk distribution.' Day 10's per-case risk scores
    and recommendations."""
    return _read_json(RESULTS_DIR / "day10_risk_scores.json") or []


def load_corrections() -> list[dict]:
    """Section 32: 'Human corrections.' Day 12's correction-memory
    records. All real entries are tagged source='simulated_demo'
    (D-057) — the dashboard must surface that tag, not present them as
    real human corrections."""
    return _read_json(RESULTS_DIR / "day12_correction_memory.json") or []


def load_workflow_versions() -> list[dict]:
    """Section 32: 'Workflow versions over time.' Day 12's V1-V4
    version history (V4 honestly reached=False, D-058)."""
    return _read_json(RESULTS_DIR / "day12_workflow_versions.json") or []


def load_failure_scenarios() -> dict | None:
    """Day 14's own new output: the 10 Section-23 failure-scenario
    results. Not one of Section 32's 8 named panels, but the brief's
    own Day-14 task, so the dashboard surfaces it as its own tab."""
    return _read_json(RESULTS_DIR / "day14_failure_scenarios.json")


def risk_distribution(risk_scores: list[dict]) -> dict[str, int]:
    """Counts cases by Day 10 recommendation — the plain aggregate
    Section 32's 'risk distribution' panel needs, computed here (not
    stored anywhere) because it's a one-line reduction, not a new
    metric that belongs in results/."""
    counts: dict[str, int] = {}
    for r in risk_scores:
        rec = r.get("recommendation", "unknown")
        counts[rec] = counts.get(rec, 0) + 1
    return counts


def all_loaded() -> dict[str, Any]:
    """Everything the dashboard needs, in one call — used by app.py and
    directly unit-tested so a missing/renamed results file is caught
    without having to run Streamlit."""
    return {
        "workflow": load_workflow_structure(),
        "shadow_run": load_shadow_run(),
        "comparisons": load_comparisons(),
        "agreement_scores": load_agreement_scores(),
        "disagreements": load_disagreements(),
        "readiness": load_readiness(),
        "risk_scores": load_risk_scores(),
        "corrections": load_corrections(),
        "versions": load_workflow_versions(),
        "failure_scenarios": load_failure_scenarios(),
    }
