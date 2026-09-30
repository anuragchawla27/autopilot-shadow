# Day 3 — Controlled mock business environment

## Done
- [x] Fault injection module (`mock_env/faults.py`) — 5 fault types, typed exceptions
- [x] Resume database + document parser mock (`mock_env/resume_db.py`)
- [x] CRM mock with update history (`mock_env/crm.py`)
- [x] Email service mock — send hard-requires approval, no real network code exists (`mock_env/email_service.py`)
- [x] Ticket system mock (`mock_env/ticket_system.py`)
- [x] `MockEnvironment` bundling all tools (`mock_env/environment.py`)
- [x] 12 synthetic resumes + 1 job description + hand-labelled ground truth (`data/`)
- [x] 16/16 tests passing covering success paths, structural faults, injected faults, and a prompt-injection resume
- [x] Decision log updated: D-016, D-017, D-018
- [x] `docs/05_mock_environment.md` written

## Deliverables committed
- `src/autopilot_shadow/mock_env/faults.py`
- `src/autopilot_shadow/mock_env/resume_db.py`
- `src/autopilot_shadow/mock_env/crm.py`
- `src/autopilot_shadow/mock_env/email_service.py`
- `src/autopilot_shadow/mock_env/ticket_system.py`
- `src/autopilot_shadow/mock_env/environment.py`
- `src/autopilot_shadow/mock_env/__init__.py`
- `data/job_description.json`
- `data/resumes.json`
- `data/ground_truth.json`
- `tests/test_mock_env_day3.py`
- `docs/05_mock_environment.md`
- `docs/02_decision_log.md` (updated)
- `daily_log/day03.md`

## Proof
```
$ python -m pytest tests/test_mock_env_day3.py -v
16 passed in 0.06s
```
Add screenshot: `daily_log/day03_test_output.png`
Add screenshot: `daily_log/day03_github_repo.png`

## Open items carried forward
- D-004: Executor (LangGraph vs custom DAG) — decide Day 7
- D-009: exact Groq model — pin when Day 4/5 need to call it

## Notes
