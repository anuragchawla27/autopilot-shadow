# Day 4 — Workflow event logger

## Done
- [x] `EventLogger` — wraps mock-tool calls into Day 2 `Event` records, catches tool errors as structured exceptions instead of crashing (`logger/event_logger.py`)
- [x] `HumanDemoPolicy` — implements Section 5's step sequence for resume screening, kept separate from the logger so Day 8's shadow engine can reuse the logger unchanged (`logger/human_demo.py`)
- [x] Dataset builder generates the full demonstration set from code, never by hand (`logger/build_dataset.py`)
- [x] `data/demonstrations.json` generated: 79 events across 15 demonstrations (74 success, 5 failure)
- [x] Policy verified against ground truth: 10/10 classifiable resumes match
- [x] Duplicate-fetch and two injected-fault scenarios (tool failure, malformed parse) added to the dataset
- [x] 18/18 tests passing
- [x] Decision log updated: D-019, D-020, D-021
- [x] `docs/06_event_logger.md` written

## Deliverables committed
- `src/autopilot_shadow/logger/event_logger.py`
- `src/autopilot_shadow/logger/human_demo.py`
- `src/autopilot_shadow/logger/build_dataset.py`
- `src/autopilot_shadow/logger/__init__.py`
- `data/demonstrations.json`
- `tests/test_event_logger_day4.py`
- `docs/06_event_logger.md`
- `docs/02_decision_log.md` (updated)
- `daily_log/day04.md`

## Proof
```
$ python -m pytest tests/test_event_logger_day4.py -v
18 passed in 0.25s

$ python -m autopilot_shadow.logger.build_dataset
Wrote 79 events across 15 demonstrations to data/demonstrations.json
```
Add screenshot: `daily_log/day04_test_output.png`
Add screenshot: `daily_log/day04_github_repo.png`

## Open items carried forward
- D-004: Executor (LangGraph vs custom DAG) — decide Day 7
- D-009: exact Groq model — pin when an LLM call is first actually needed (likely Day 5 or 6, for reasoning_summary generation or ambiguous-case handling)

## Notes
