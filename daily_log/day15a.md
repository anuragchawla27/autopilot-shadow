# Day 15, Part A — Experiments A-E and Ablation A-E

Day 15 is split into two parts (your call): **Part A** (this entry) covers
Sections 30/31 — the controlled experiments and ablation study. **Part B**
(separate entry) covers the final report, demo video, and presentation
(Section 36 items 19-21, Section 37). Nothing from either part is committed
to git until both are done and confirmed.

## Done
- [x] `experiments/case_outcome.py` — one shared `CaseOutcome` shape every configuration reduces to, so all 10 configurations (5 experiments + 5 ablation systems) are compared on exactly the same metrics
- [x] `experiments/engine.py` — `aggregate()`: Section 30's required metrics (automation coverage, human interventions, errors, false automation, unsafe sends, workflow completion) computed once, reused by both studies
- [x] `experiments/naive_executor.py`, `confidence_only_executor.py`, `risk_aware_executor.py` — the three new executor configurations Section 30 asks for; C and D reuse Day 7/10's real components unchanged (D-074)
- [x] `experiments/build_experiments.py` — runs real data through all 5 experiments, writes `results/day15_experiments.json`
- [x] **Real finding**: naive auto-execution (Experiment B) produces 6 unsafe interview invitations out of 12 cases — a concrete, measured instance of Section 1's own opening warning. Confidence-only gating (D) cuts that to 3, not 0. Only the risk model (E) and step-level human approval (C) reach 0.
- [x] `experiments/bare_decision.py`, `ablation_executors.py`, `ablation_engine.py` — Ablation Systems A-E; A/B are an honestly-reframed "LLM automation only" substitute since this project has never called an LLM (D-075)
- [x] `experiments/build_ablation.py` — writes `results/day15_ablation.json`
- [x] **Real finding**: Systems A and B's only false automation is `res_0012`, the project's own deliberately adversarial prompt-injection resume — wrongly shortlisted by any decision-maker lacking an injection check, correctly caught the moment System C's real classifier re-enters (D-077)
- [x] **Bug caught and documented, not silently fixed**: `BareNoStructureExecutor` originally logged its decision under the wrong action name, silently inflating System A's unsafe-send count from 5 to 10 (D-078)
- [x] 21/21 new tests passing; full suite 218/218 passing
- [x] Decision log updated: D-074 through D-078
- [x] `docs/18_experiments_and_ablation.md` written

## Deliverables (Part A, not yet committed)
- `src/autopilot_shadow/experiments/` (10 files: `__init__.py`, `case_outcome.py`, `engine.py`, `naive_executor.py`, `confidence_only_executor.py`, `risk_aware_executor.py`, `build_experiments.py`, `bare_decision.py`, `ablation_executors.py`, `ablation_engine.py`, `build_ablation.py`)
- `results/day15_experiments.json`
- `results/day15_ablation.json`
- `tests/test_experiments_day15.py`
- `tests/test_ablation_day15.py`
- `docs/18_experiments_and_ablation.md`
- `docs/02_decision_log.md` (updated: D-074 - D-078)
- `daily_log/day15a.md` (this file)

## Proof
```
$ python -m autopilot_shadow.experiments.build_experiments
$ python -m autopilot_shadow.experiments.build_ablation

$ python -m pytest tests/test_experiments_day15.py tests/test_ablation_day15.py -v
21 passed

$ python -m pytest tests/ -q
218 passed
```

## Open items carried to Part B
- Final engineering report (Section 37 structure) — a first draft already
  exists (`docs/19_final_engineering_report.md`) from earlier work this
  session; needs review against the final Part A numbers above before
  being treated as done.
- Demonstration video, final presentation — not started.
- D-009: exact Groq/LLM model — still unpinned; by Day 15's own ablation
  result (D-075/D-077), this project's deterministic rule-based decisions
  already outperform what an opaque decision-maker without structure
  would do on the one adversarial case that matters, which is itself a
  finding worth stating plainly in the final report rather than treated
  as an unexamined gap.

## Notes
Two genuinely new engineering pieces this part, both honestly reframed
rather than faked: Section 31's "LLM automation only" baseline (no LLM
exists in this codebase — D-075) and the shared `CaseOutcome`/`aggregate()`
design that lets 10 different configurations be compared on identical
terms without 10 different ad hoc scoring functions. The most important
single result from either study is `res_0012`: it is the only case in
either study where something gets automated wrongly, and it is wrong in
exactly the way the project's own safety design (injection detection,
Day 7; risk override, Day 10) exists to catch.
