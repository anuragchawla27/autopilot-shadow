"""
Diffs two WorkflowVersions (Day 12, Section 25: "Track changed steps,
rules, risk, agreement, and outcomes").

Deliberately generic: it diffs whatever `metrics` dict each version
actually carries (built from real per-day results files in
`workflow_version.py`) rather than hand-listing per-version special
cases — a version this project adds later (V5, V6...) is diffable
without touching this module.
"""

from __future__ import annotations

from .workflow_version import WorkflowVersion


def diff(v_from: WorkflowVersion, v_to: WorkflowVersion) -> dict:
    changed = {}
    all_keys = set(v_from.metrics) | set(v_to.metrics)
    for key in sorted(all_keys):
        before = v_from.metrics.get(key, "<not tracked>")
        after = v_to.metrics.get(key, "<not tracked>")
        if before != after:
            changed[key] = {"before": before, "after": after}

    return {
        "from_version": v_from.version,
        "from_label": v_from.label,
        "to_version": v_to.version,
        "to_label": v_to.label,
        "reached_change": None if v_from.reached == v_to.reached else {"before": v_from.reached, "after": v_to.reached},
        "changed_metrics": changed,
    }


def diff_all_consecutive(versions: list[WorkflowVersion]) -> list[dict]:
    return [diff(versions[i], versions[i + 1]) for i in range(len(versions) - 1)]
