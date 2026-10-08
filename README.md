# AUTOPILOT SHADOW

AI workflow reconstruction, shadow execution and automation-readiness assessment.
A 15-day advanced AI automation project (PranavX Labs challenge).

## What it does

```
OBSERVE → RECONSTRUCT → PROPOSE → SHADOW → COMPARE → LEARN → ASSESS → APPROVE → AUTOMATE
```

The system studies how humans performed a business workflow, builds a structured version of it, generates an automation, and runs it in **shadow mode** (it proposes actions but takes no irreversible ones). It then compares AI vs human decisions and reports how ready the workflow is for automation.

**Core question:** *When should an AI workflow be trusted enough to automate?*

**Demo workflow:** HR resume screening, on synthetic data and mock tools only.

## Safety

- All data is synthetic. No real candidates, emails or company systems.
- Shadow mode never performs irreversible actions.
- Human decisions are never silently overwritten.
- Every reported metric comes from an actual experiment run.

See `docs/01_problem_scope_safety.md`.

## Docs

- `docs/01_problem_scope_safety.md` — problem, workflow choice, scope, safety
- `docs/02_decision_log.md` — technology and design decisions
- `docs/03_established_vs_own_design.md` — established techniques vs our design
- `daily_log/` — one entry per day with proof of completion

## Progress

- [x] Day 1 — Problem, workflow selection, safety
- [x] Day 2 — Event schema and architecture
- [x] Day 3 — Mock business environment
- [x] Day 4 — Workflow event logger
- [x] Day 5 — Workflow reconstruction engine
- [x] Day 6 — Decision and condition extraction
- [x] Day 7 — Automation generator
- [x] Day 8 — Shadow execution
- [x] Day 9 — Human–AI comparison engine
- [x] Day 10 — Confidence and risk scoring
- [x] Day 11 — Disagreement, exceptions, approval gates
- [ ] Day 12 — Correction memory and versioning
- [ ] Day 13 — Automation-readiness evaluation
- [ ] Day 14 — Failure scenarios and dashboard
- [ ] Day 15 — Experiments, report, demo

## Status

Work in progress. Repo structure grows day by day.
