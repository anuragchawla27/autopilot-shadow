# Day 7 — Automation generator

## Done
- [x] Automation classifier: 6 explicit criteria, applied in order, every step gets a real reason (`generator/classifier.py`)
- [x] D-004 resolved: custom DAG runner chosen over LangGraph, documented reasoning (`generator/executor.py`)
- [x] Generic action handlers so the Workflow graph itself is the executable spec, not a separate hardcoded script (`generator/handlers.py`)
- [x] Caught and fixed a real mismatch against Section 4's own table (skill matching needed explicit monitoring, not plain automate)
- [x] Caught and fixed a real sequencing bug in the executor (decision attached before handler ran) — fixed with a backward-compatible EventLogger flag, not a closure hack
- [x] Refactored shared feature utilities out of Day 4's private functions into `common/feature_utils.py`
- [x] Real executor dry-run against mock tools for both an easy and an ambiguous resume — proven with an actual mock-environment side effect, not a stub
- [x] Honest finding documented: step-level classification means both resumes halt at the same step; per-instance routing is explicitly Day 10/11's job
- [x] 11/11 new tests passing; full suite 70/70 passing
- [x] Decision log updated: D-029 through D-033 (plus D-004 resolved)
- [x] `docs/09_automation_generator.md` written

## Deliverables committed
- `src/autopilot_shadow/generator/classifier.py`
- `src/autopilot_shadow/generator/risk_profile.py`
- `src/autopilot_shadow/generator/executor.py`
- `src/autopilot_shadow/generator/handlers.py`
- `src/autopilot_shadow/generator/build_automation.py`
- `src/autopilot_shadow/generator/__init__.py`
- `src/autopilot_shadow/common/feature_utils.py`
- `src/autopilot_shadow/common/__init__.py`
- `src/autopilot_shadow/logger/event_logger.py` (updated — new optional flag, backward-compatible)
- `src/autopilot_shadow/logger/human_demo.py` (updated — uses shared feature_utils)
- `data/workflow_classified.json`
- `results/day07_classification.json`
- `results/day07_executor_dry_run.json`
- `tests/test_automation_generator_day7.py`
- `docs/09_automation_generator.md`
- `docs/02_decision_log.md` (updated)
- `daily_log/day07.md`

## Proof
```
$ python -m pytest tests/test_automation_generator_day7.py -v
11 passed in 0.14s

$ python -m pytest tests/ -q
70 passed in 0.23s

$ python -m autopilot_shadow.generator.build_automation
  compare_skills -> automate_with_monitoring (risk=low)
  classify_candidate -> human_review (risk=medium)
  send_interview_invitation -> human_review (risk=high)
res_0001: 5 events, halted at action='classify_candidate' approval='pending'
res_0004: 5 events, halted at action='classify_candidate' approval='pending'
```
Add screenshot: `daily_log/day07_test_output.png`
Add screenshot: `daily_log/day07_github_repo.png`

## Open items carried forward
- D-009: exact Groq model — pin when an LLM call is first actually needed
- Day 8 will reuse `generator/handlers.py` for the AI's proposed-action side of shadow mode
- Day 10/11 must add per-instance confidence routing so easy cases (res_0001) can eventually proceed past a HUMAN_REVIEW step while hard cases (res_0004) still halt

## Notes
