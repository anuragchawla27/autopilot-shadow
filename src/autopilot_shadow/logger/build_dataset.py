"""
Generates the full set of human workflow demonstrations by running
`run_human_demo` (Day 4 policy) over every synthetic resume (Day 3 data)
against a fresh MockEnvironment, plus a few demos that deliberately
exercise duplicate-submission and injected-fault paths.

Output: data/demonstrations.json — a flat list of serialized Events,
grouped by demo_id. This is the exact "set of historical workflow
demonstrations" Section 5 of the brief asks for, and is what Day 5's
reconstruction engine will read.

Run: python -m autopilot_shadow.logger.build_dataset
"""

from __future__ import annotations

import json
from pathlib import Path

from autopilot_shadow.mock_env.environment import MockEnvironment
from autopilot_shadow.mock_env.faults import FaultType
from autopilot_shadow.schemas.event import ActorType

from .human_demo import run_human_demo

# .../src/autopilot_shadow/logger/build_dataset.py -> parents[3] == project root
DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def _load_json(name: str):
    return json.loads((DATA_DIR / name).read_text())


def build_all_demonstrations() -> list[dict]:
    resumes = _load_json("resumes.json")
    job_description = _load_json("job_description.json")
    resume_ids = [r["resume_id"] for r in resumes]

    all_events: list[dict] = []

    # 1) One plain demo per resume, fresh environment each time. Faults for
    #    res_0009 (missing info) and res_0010 (malformed skills) surface
    #    naturally here because DocumentParser detects them structurally —
    #    no fault= injection needed for those two.
    for i, resume_id in enumerate(resume_ids, start=1):
        env = MockEnvironment(resumes)
        logger = run_human_demo(
            env, job_description, resume_id, demo_id=f"demo_{i:04d}_{resume_id}"
        )
        all_events.extend(e.model_dump(mode="json") for e in logger.events)

    # 2) Duplicate-submission demo: fetch the same resume twice within one
    #    demo (Section 23 Case 8). Second fetch raises
    #    DuplicateResumeAlreadyFetched, logged as a failure Event.
    env = MockEnvironment(resumes)
    dup_logger = run_human_demo(env, job_description, "res_0011", demo_id="demo_dup_0001_res_0011")
    # second pass through the SAME logger/env to force the duplicate fetch
    extra_fetch = dup_logger.log_action(
        actor="hr_reviewer_1",
        actor_type=ActorType.HUMAN,
        application="resume_db",
        action="fetch_resume",
        input_data={"resume_id": "res_0011"},
        fn=lambda: env.resume_db.fetch_resume("res_0011"),
    )
    all_events.extend(e.model_dump(mode="json") for e in dup_logger.events)

    # 3) Injected-fault demos: force TOOL_FAILURE on fetch and API_TIMEOUT
    #    on a CRM update, so the dataset also contains these two fault
    #    types explicitly (not just the structurally-detected ones above).
    env = MockEnvironment(resumes)
    tool_failure_logger = run_human_demo(
        env, job_description, "res_0001", demo_id="demo_fault_tool_failure", fault_on_fetch=FaultType.TOOL_FAILURE
    )
    all_events.extend(e.model_dump(mode="json") for e in tool_failure_logger.events)

    env = MockEnvironment(resumes)
    parse_fail_logger = run_human_demo(
        env, job_description, "res_0003", demo_id="demo_fault_malformed_parse", fault_on_parse=FaultType.MALFORMED_INPUT
    )
    all_events.extend(e.model_dump(mode="json") for e in parse_fail_logger.events)

    return all_events


def main() -> None:
    events = build_all_demonstrations()
    out_path = DATA_DIR / "demonstrations.json"
    out_path.write_text(json.dumps(events, indent=2, default=str))
    demo_ids = sorted(set(e["demo_id"] for e in events))
    print(f"Wrote {len(events)} events across {len(demo_ids)} demonstrations to {out_path}")


if __name__ == "__main__":
    main()
