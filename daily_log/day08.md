# Day 8 — Shadow execution

## Done
- [x] `ShadowExecutor` — runs every workflow step for every case, never halts (unlike Day 7's `AutomationExecutor`), per Section 12
- [x] Fresh `MockEnvironment` per shadow run — avoids a false-positive duplicate-fetch error, mirrors independent observation
- [x] Shadow-safe handlers — no real CRM write, no real email send, only `draft_email` (structurally proven never to call `send_email`)
- [x] Provisional confidence model tied to which Day 6 rule explains the actual decision (`shadow/confidence.py`), explicitly placeholder pending Day 10
- [x] **3 real bugs caught by running the code and fixed**: mismatched confidence field names (all cases showing 0.3), unconditional email drafting for rejected candidates, and confidence picking a rule that didn't match the actual decision made
- [x] New shared utility `common/rule_evaluation.py` — operator-aware rule matching, reusable by Day 10
- [x] `EventLogger` extended with `confidence_from_result` (backward-compatible, same pattern as Day 7's `decision_from_result`)
- [x] Full 12-resume shadow run generated: 74 events, `data/shadow_run.json`
- [x] 12/12 new tests passing; full suite 82/82 passing
- [x] Decision log updated: D-034 through D-039
- [x] `docs/10_shadow_execution.md` written

## Deliverables committed
- `src/autopilot_shadow/shadow/shadow_executor.py`
- `src/autopilot_shadow/shadow/shadow_handlers.py`
- `src/autopilot_shadow/shadow/confidence.py`
- `src/autopilot_shadow/shadow/build_shadow_run.py`
- `src/autopilot_shadow/shadow/__init__.py`
- `src/autopilot_shadow/common/rule_evaluation.py`
- `src/autopilot_shadow/generator/handlers.py` (updated — stores `injection_detected` into ctx)
- `src/autopilot_shadow/logger/event_logger.py` (updated — new optional flag, backward-compatible)
- `data/shadow_run.json`
- `results/day08_shadow_run_summary.json`
- `tests/test_shadow_execution_day8.py`
- `docs/10_shadow_execution.md`
- `docs/02_decision_log.md` (updated)
- `daily_log/day08.md`

## Proof
```
$ python -m pytest tests/test_shadow_execution_day8.py -v
12 passed in 0.12s

$ python -m pytest tests/ -q
82 passed in 0.28s

$ python -m autopilot_shadow.shadow.build_shadow_run
Shadow-executed 12 resumes, 74 total proposed events.
res_0012: ... proposed='human_review', confidence=0.4   (correctly NOT 0.95 after the fix)
```
Add screenshot: `daily_log/day08_test_output.png`
Add screenshot: `daily_log/day08_github_repo.png`

## Open items carried forward
- D-009: exact Groq model — pin when an LLM call is first actually needed
- Day 9 reads `data/demonstrations.json` (human) alongside `data/shadow_run.json` (AI) to build the comparison engine
- Day 10 replaces the provisional confidence model in `shadow/confidence.py` with the full weighted risk model (Section 10)

## Notes
Three real bugs were caught and fixed today purely by running the shadow batch and reading its actual output line by line, rather than trusting that the code "looked right." All three are documented in detail in docs/10 and in the decision log (D-036, D-037, D-038) with the exact symptom that revealed each one.
