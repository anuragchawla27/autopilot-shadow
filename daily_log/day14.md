# Day 14 — Failure scenarios and dashboard

## Done
- [x] `failure_scenarios/tool_contracts.py` — minimum per-action output contract + validator; closes Section 20's "validate outputs" gap that no prior day implemented
- [x] `failure_scenarios/wrong_tool_harness.py` — Case 2 harness (no real tool-selection branch exists in this workflow, so this is a clearly-labelled synthetic construction, same honesty pattern as D-043/D-054/D-057)
- [x] `failure_scenarios/calibration.py` — Case 3: real Expected Calibration Error (against ground truth, not the same-author human policy) + a synthetic high-confidence-wrong safety check against Section 22's hard override
- [x] `failure_scenarios/scenarios.py` — all 10 Section 23 cases, 8 of them driven unchanged by real Days 3/8/9/10/11 mechanisms
- [x] `failure_scenarios/build_failure_report.py` — generates `results/day14_failure_scenarios.json` from real runs (S7)
- [x] **Result: 10/10 cases fail safely** (real run, not asserted)
- [x] **Honest new finding**: real calibration ECE = 0.27 on 10 scored classify_candidate cases (reported plainly, not tuned)
- [x] `dashboard/data_loader.py` — pure, Streamlit-free data access, one function per Section 32 panel
- [x] `dashboard/app.py` — 9-tab Streamlit app (the 8 Section 32 panels + Day 14's own failure-scenarios tab); headline banner surfaces Day 13's Shadow Score/readiness tier directly, nothing recomputed
- [x] Dashboard verified headless via Streamlit's own `AppTest` runner against real result files — 0 exceptions, 0 warnings
- [x] 29 new tests (18 failure scenarios + 11 dashboard data loader), all passing on the first run; full suite 197/197 passing
- [x] Decision log updated: D-065 through D-071
- [x] `docs/16_failure_scenarios_dashboard.md` written
- [x] `docs/03_established_vs_own_design.md` status table filled in retroactively for Days 2-13, plus Day 14's own rows

## Deliverables committed
- `src/autopilot_shadow/failure_scenarios/__init__.py`
- `src/autopilot_shadow/failure_scenarios/tool_contracts.py`
- `src/autopilot_shadow/failure_scenarios/wrong_tool_harness.py`
- `src/autopilot_shadow/failure_scenarios/calibration.py`
- `src/autopilot_shadow/failure_scenarios/scenarios.py`
- `src/autopilot_shadow/failure_scenarios/build_failure_report.py`
- `results/day14_failure_scenarios.json`
- `dashboard/__init__.py`
- `dashboard/data_loader.py`
- `dashboard/app.py`
- `tests/test_failure_scenarios_day14.py`
- `tests/test_dashboard_data_day14.py`
- `docs/16_failure_scenarios_dashboard.md`
- `docs/02_decision_log.md` (updated)
- `docs/03_established_vs_own_design.md` (updated)
- `requirements.txt` (updated: streamlit, pandas)
- `daily_log/day14.md`

## Proof
```
$ python -m autopilot_shadow.failure_scenarios.build_failure_report
FAILURE SCENARIOS: 10 / 10 fail safely

  [PASS] case_1: AI extracts incorrect information
  [PASS] case_2: AI selects incorrect tool
  [PASS] case_3: AI has high confidence but is wrong
  [PASS] case_4: AI encounters missing information
  [PASS] case_5: Tool returns malformed output
  [PASS] case_6: Human and AI disagree
  [PASS] case_7: Workflow contains an exception
  [PASS] case_8: Same request is processed twice
  [PASS] case_9: External action requires approval
  [PASS] case_10: AI attempts action classified as high risk

$ python -m pytest tests/test_failure_scenarios_day14.py tests/test_dashboard_data_day14.py -v
29 passed

$ python -m pytest tests/ -q
197 passed in 0.42s

$ streamlit run dashboard/app.py
  (verified headless via streamlit.testing.v1.AppTest — 0 exceptions)
```
Add screenshot: `daily_log/day14_test_output.png`
Add screenshot: `daily_log/day14_dashboard.png` (run `streamlit run dashboard/app.py` locally and screenshot the browser tab)
Add screenshot: `daily_log/day14_github_repo.png`

## Open items carried forward
- D-009: exact Groq model — still unpinned; no LLM call exists anywhere in this codebase through Day 14
- Day 15: Experiments A-E, ablations A-E, final report, demo video, presentation (Sections 30/31/36/37) — not started
- Only the `day-01` tag was ever actually pushed to GitHub in this repo's history — `day-02` through `day-13` commits exist but were never tagged; fixing this (tagging all of day-02..day-14 now) is part of today's git steps

## Notes
Two of the 10 Section 23 cases (tool selection, calibration) had no real code path to exercise because this workflow's action-to-tool mapping is fixed 1:1 and no calibration check existed before today — both gaps are documented honestly in `docs/16` and the decision log (D-065 through D-068) rather than silently worked around or skipped. The dashboard deliberately carries forward every prior day's honest finding instead of smoothing it over: 0 real disagreements, all corrections tagged `simulated_demo`, V4 shown as not yet reached.
