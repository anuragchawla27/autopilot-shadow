# 17 — Requirements Traceability (before Day 15)

**Why this doc exists.** Before starting Day 15 (the last day), this is a
direct, line-by-line check of the repo against the brief's own two
checklists — Section 36 ("Final Deliverables," 21 items) and Section 39
("Project Success Criteria," 13 items) — plus a note on the one real
documentation mismatch this check caught. The goal is a straight answer to
"is this project actually correct," backed by file paths and real test
output, not reassurance.

**How to read the status column.** ✅ = built, tested, verified against real
data. ⏳ = explicitly planned for Day 15 (the brief's own 15-day plan puts
it there — Section 35 assigns "Final experiments, documentation, demo and
presentation" to Day 15). ⚠️ = a real gap or caveat worth knowing about,
explained inline.

## Section 36 — Final Deliverables (21 items)

| # | Deliverable | Status | Evidence |
|---|---|---|---|
| 1 | Source-code repository | ✅ | `github.com/anuragchawla27/autopilot-shadow`, 14 commits, 14 tags (day-01..day-14) |
| 2 | Working AI prototype | ✅ | `src/autopilot_shadow/` — runs end to end, `python -m autopilot_shadow.readiness.build_readiness` etc. all execute against real data |
| 3 | Workflow reconstruction | ✅ | `reconstruction/engine.py`, real output `data/reconstructed_workflow_v1.json`, evaluated in `results/day05_reconstruction_evaluation.json` |
| 4 | Workflow schema | ✅ | `schemas/event.py`, `schemas/workflow.py` — Pydantic-validated, `tests/test_schemas_day2.py` |
| 5 | Automation generator | ✅ | `generator/classifier.py`, `generator/executor.py` — 5-category classification, `results/day07_classification.json` |
| 6 | Shadow execution engine | ✅ | `shadow/shadow_executor.py` — 74 real shadow events in `data/shadow_run.json`, never calls `send_email` (AST-proven) |
| 7 | Human–AI comparison | ✅ | `comparison/engine.py` — 5 separate dimensions, never collapsed (Section 14's own rule), `results/day09_comparisons.json` |
| 8 | Risk/confidence module | ✅ | `risk/risk_model.py` — documented weighted formula + 2 hard overrides, `results/day10_risk_scores.json` |
| 9 | Exception handling | ✅ | `exceptions/detector.py` — Section 17's 3-trigger rule, `results/day11_exceptions.json` |
| 10 | Correction memory | ✅ | `correction/memory.py` — plain retrieval, `results/day12_correction_memory.json` (honestly tagged `simulated_demo`, see item 16's caveat) |
| 11 | Workflow versioning | ✅ | `versioning/workflow_version.py` — V1-V4, `results/day12_workflow_versions.json` (V4 honestly `reached=False`) |
| 12 | Readiness assessment | ✅ | `readiness/shadow_score.py` + `readiness_decision.py` — `results/day13_readiness_assessment.json`, Shadow Score 74.24, tier HUMAN_IN_THE_LOOP_READY |
| 13 | Mock tool environment | ✅ | `mock_env/` — resume DB, CRM, email, parser, ticket system, all with deterministic fault injection (`faults.py`) |
| 14 | Dashboard/demo | ✅ | `dashboard/app.py` — 9 tabs (Section 32's 8 + Day 14's own), verified headless via `AppTest`, confirmed live by you across all 9 tabs |
| 15 | Test dataset | ✅ | `data/resumes.json` (12 synthetic resumes), `data/job_description.json`, `data/ground_truth.json` (independently hand-labelled) |
| 16 | Evaluation results | ✅ | `results/day05_*.json` through `results/day14_*.json` — 18 result files, every one script-generated (S7) |
| 17 | Architecture diagram | ✅* | `docs/04_architecture.md` §3 — ASCII pipeline diagram, text-based not a rendered image. *Acceptable as written; a rendered image (draw.io/Mermaid export) would be a Day 15 polish item, not a requirement — the brief doesn't specify format |
| 18 | Technical documentation | ✅ | `docs/01` through `docs/17` (this doc) — one doc per component, plus `daily_log/day01.md`..`day14.md` |
| 19 | Final engineering report | ⏳ Day 15 | Section 37's structure (Abstract → Conclusion) — not started |
| 20 | Demonstration video | ⏳ Day 15 | Not started |
| 21 | Final presentation | ⏳ Day 15 | Not started |

**18 of 21 done. The remaining 3 are explicitly Day 15's job per the brief's own schedule** (Section 35: "DAY 15 — Final experiments, documentation, demo and presentation"), not things skipped.

## Section 39 — Project Success Criteria (13 items)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Correct workflow reconstruction | ✅ | `results/day05_reconstruction_evaluation.json` — step_recall 1.0, edge_recall 1.0 |
| 2 | Structured decision extraction | ✅ | `results/day06_decision_extraction.json` — explicit/inferred/unknown, every rule labelled |
| 3 | Generation of executable automation logic | ✅ | `generator/build_automation.py` produces `data/workflow_classified.json`, actually runnable by `AutomationExecutor` |
| 4 | Safe shadow execution | ✅ | `shadow/shadow_executor.py` — never commits a real action; 10/10 Day 14 failure scenarios fail safely |
| 5 | Human–AI comparison | ✅ | `results/day09_agreement_scores.json` — 5 dimensions, with the same-author caveat documented (D-043) rather than overclaimed |
| 6 | Confidence-aware decisions | ✅ | `shadow/confidence.py` — ties confidence to which Day 6 rule actually explains the outcome |
| 7 | Risk-aware automation | ✅ | `risk/risk_model.py` — 2 hard overrides that no formula can automate away |
| 8 | Exception handling | ✅ | `exceptions/detector.py` + Day 14 Cases 1/4/5/7 prove it against real forced faults |
| 9 | Human approval mechanisms | ✅ | `exceptions/approval_gate.py` — 4-state gate, structurally provable that only `apply_decision` can resolve PENDING |
| 10 | Learning from corrections | ✅ | `correction/memory.py` — honestly labelled synthetic-demo data, since no live human-approval UI exists yet (D-057) |
| 11 | Quantitative evaluation | ✅ | `readiness/metrics.py` — reconstruction/decision/agreement/risk metrics, all real numbers |
| 12 | Failure analysis | ✅ | Day 14: all 10 Section 23 cases, `results/day14_failure_scenarios.json` |
| 13 | Clear automation-readiness criteria | ✅ | `readiness/readiness_decision.py` — 4 ordered tiers, each with an explicit, testable condition |

**13 of 13 met**, each with a real, re-runnable source — not a claim without evidence.

## The one real correction this check produced

`docs/04_architecture.md` (Day 2) described a planned `api/` FastAPI layer
and said the dashboard would be "built incrementally from Day 9." Neither
happened: no `api/` directory was ever created, and the dashboard was built
in one pass on Day 14. This wasn't a project failure — Day 14 made a
deliberate, documented call (see `docs/16`, D-069/D-070) that the dashboard
only ever needs to **read** results a script already computed, never
trigger live computation, so a request/response API had no real job to do.
`docs/04` has been corrected to match what was actually built, and D-072 /
D-073 in the decision log record the reasoning, including the direct
"is a backend missing" question this traces back to: **no — `src/autopilot_shadow/`
is the backend, it's just not exposed over HTTP, which the brief never
asks for** (Section 34 explicitly allows alternatives to the "possible
stack," and Section 36/39 never name an API server as a requirement).

## On n8n / "is this really automation"

Documented at the time (D-005) and re-confirmed here: Section 34 lists n8n
as something to use only "where appropriate," and Section 11 lists a
custom Python workflow as an equally valid representation alongside n8n,
LangGraph, DAGs, and state machines. The actual automation in this project
is `generator/executor.py` (`AutomationExecutor`) and `shadow/shadow_executor.py`
(`ShadowExecutor`) — both walk the reconstructed workflow and automatically
decide/act per step from the extracted rules and risk model, with no human
touching each individual case. That is Section 2's "core objective,"
independent of which orchestration tool carries it out.

## What this means for Day 15

Nothing above blocks starting Day 15. The pipeline, the mock environment,
the dashboard, and the failure-scenario testing are all built, tested
(197/197), and verified against real data. Day 15's actual job — per
Section 30/31/36/37 — is Experiments A-E, Ablation A-E, the final report,
and the demo materials, all of which run ON TOP of what already exists
rather than filling a structural gap underneath it.
