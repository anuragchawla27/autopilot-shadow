"""
Builds and writes this project's real 4-version workflow history and
the diffs between consecutive versions (Day 12, Section 25).

Run: python -m autopilot_shadow.versioning.build_versions
"""

from __future__ import annotations

import json
from pathlib import Path

from .version_diff import diff_all_consecutive
from .workflow_version import build_versions

ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = ROOT / "results"


def main() -> None:
    versions = build_versions()
    diffs = diff_all_consecutive(versions)

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "day12_workflow_versions.json").write_text(
        json.dumps([v.as_dict() for v in versions], indent=2, default=str)
    )
    (RESULTS_DIR / "day12_version_diffs.json").write_text(json.dumps(diffs, indent=2, default=str))

    print("Workflow versions:")
    for v in versions:
        status = "REACHED" if v.reached else "NOT YET REACHED"
        print(f"  V{v.version} {v.label:<30} ({status}, Day {v.built_in_day})")

    print("\nDiffs between consecutive versions:")
    for d in diffs:
        print(f"  V{d['from_version']} -> V{d['to_version']}: {len(d['changed_metrics'])} metric(s) changed")
        for key, change in d["changed_metrics"].items():
            print(f"    {key}: {change['before']} -> {change['after']}")

    print("\nWrote: results/day12_workflow_versions.json, results/day12_version_diffs.json")


if __name__ == "__main__":
    main()
