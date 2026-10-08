# Day 12 — Correction memory and workflow versioning

## Done
- [x] `correction/schema.py` — Section 24's exact record shape (Original AI Decision, Human Correction, Evidence, Workflow Context, Reason, Timestamp)
- [x] `correction/memory.py` — plain, most-recent-first retrieval-by-action store (deliberately not embeddings/semantic search — Section 24 explicitly warns against the most complex approach, blind retraining)
- [x] `correction/from_approval.py` — builds a correction record from a Day 11 approval outcome; structurally refuses to store `approve` decisions (not a correction)
- [x] `correction/build_correction_memory.py` — runs a small, fully-visible, FIXED reference policy over Day 11's real 16-item approval queue, **clearly tagged `source="simulated_demo"`** since this project has no live human-in-the-loop UI yet
- [x] `versioning/workflow_version.py` — the brief's own 4-tier version progression (Manual -> Shadow -> Risk-Aware HITL -> High-Confidence), V1-V3 built from real prior-day results files, V4 honestly `reached=False` with empty metrics
- [x] `versioning/version_diff.py` — generic metric-by-metric diff between any two versions, plus a `reached`-state-change flag
- [x] `versioning/build_versions.py` — builds and writes the real 4-version history and all 3 consecutive diffs
- [x] 22/22 new tests passing on the first run (no bugs this time); full suite 151/151 passing
- [x] Decision log updated: D-055 through D-059
- [x] `docs/14_correction_memory_versioning.md` written

## Deliverables committed
- `src/autopilot_shadow/correction/__init__.py`
- `src/autopilot_shadow/correction/schema.py`
- `src/autopilot_shadow/correction/memory.py`
- `src/autopilot_shadow/correction/from_approval.py`
- `src/autopilot_shadow/correction/build_correction_memory.py`
- `src/autopilot_shadow/versioning/__init__.py`
- `src/autopilot_shadow/versioning/workflow_version.py`
- `src/autopilot_shadow/versioning/version_diff.py`
- `src/autopilot_shadow/versioning/build_versions.py`
- `results/day12_correction_memory.json`
- `results/day12_workflow_versions.json`
- `results/day12_version_diffs.json`
- `tests/test_correction_versioning_day12.py`
- `docs/14_correction_memory_versioning.md`
- `docs/02_decision_log.md` (updated)
- `daily_log/day12.md`

## Proof
```
$ python -m pytest tests/test_correction_versioning_day12.py -v
22 passed in 0.08s

$ python -m pytest tests/ -q
151 passed in 0.41s

$ python -m autopilot_shadow.correction.build_correction_memory
[SIMULATED DEMO — see module docstring] Stored 16 correction records from 16 real Day 11 approval-queue items.

Correction count by action:
  classify_candidate           4
  extract_resume               2
  send_interview_invitation    10

$ python -m autopilot_shadow.versioning.build_versions
Workflow versions:
  V1 Manual                         (REACHED, Day 4)
  V2 AI-Proposed (Shadow)           (REACHED, Day 8)
  V3 Risk-Aware Human-in-the-Loop   (REACHED, Day 11)
  V4 High-Confidence Automation     (NOT YET REACHED, Day 13)
```
Add screenshot: `daily_log/day12_test_output.png`
Add screenshot: `daily_log/day12_github_repo.png`

## Open items carried forward
- D-009: exact Groq model — pin when an LLM call is first actually needed
- Day 13's readiness assessment (Section 26) reads `results/day12_workflow_versions.json` and `results/day12_version_diffs.json` directly as the real evidence for whether V4 is justified
- The correction memory's real-data run is explicitly simulated/demo data (`source="simulated_demo"`), not a real evaluation result — flagged honestly rather than left ambiguous, since Day 14's dashboard is where a real human-in-the-loop UI finally exists

## Notes
No real bugs this time — all 22 new tests passed on the first run. The main judgment call was how to handle Section 24 honestly given this project has no live approval UI yet: rather than either faking real-looking correction data or leaving the storage mechanism completely unexercised against real queue shapes, the build script runs a small, fully-disclosed reference policy and tags every record it produces as simulated — same honesty pattern as Day 9's synthetic mismatch tests, just applied to a demo data run instead of only unit tests.
