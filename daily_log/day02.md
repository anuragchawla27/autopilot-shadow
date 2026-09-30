# Day 2 — Workflow event schema and system architecture

## Done
- [x] Event schema defined (`src/autopilot_shadow/schemas/event.py`)
- [x] Workflow schema defined (`src/autopilot_shadow/schemas/workflow.py`)
- [x] Both schemas validated against realistic resume-screening data — 7/7 tests passing
- [x] System architecture documented, mapped to brief's Section 33 diagram
- [x] Decision log updated: D-009 (Groq) accepted, D-013/D-014/D-015 added for schema design choices
- [x] `requirements.txt` started (pydantic, pytest)

## Deliverables committed
- `src/autopilot_shadow/schemas/event.py`
- `src/autopilot_shadow/schemas/workflow.py`
- `tests/test_schemas_day2.py`
- `docs/04_architecture.md`
- `docs/02_decision_log.md` (updated)
- `requirements.txt`
- `daily_log/day02.md`

## Proof
```
$ python -m pytest tests/test_schemas_day2.py -v
7 passed in 0.11s
```
Add screenshot: `daily_log/day02_test_output.png` (terminal showing the 7 passing tests)
Add screenshot: `daily_log/day02_github_repo.png` (GitHub repo page showing the day02 commit)

## Open items carried forward
- D-004: Executor (LangGraph vs custom DAG) — decide Day 7
- D-009: exact Groq model — pin once mock environment exists (Day 3+)

## Notes
