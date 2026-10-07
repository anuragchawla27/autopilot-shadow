# Day 9 — Human-AI comparison engine

## Done
- [x] `comparison/engine.py` — aligns human (Day 4) and AI shadow (Day 8) traces by `resume_id`/action, normalizes each action's different field shapes into one canonical comparable form, per Section 13
- [x] Handles the documented logging-granularity asymmetry: AI shadow always logs `send_interview_invitation` even as a no-op; human demo only logs it on shortlist — treated as outcome-equivalent, not a mismatch
- [x] Handles failed steps by comparing `exception_type` instead of the (trivially empty) `output` dict — a real signal, not a coincidental one
- [x] `comparison/agreement.py` — Section 14's five SEPARATE dimensions (action/data/decision/tool/outcome), never merged into one number, at both per-resume and dataset level
- [x] `comparison/build_comparison.py` — runs the full 12-resume comparison and writes results
- [x] Honest finding: real dataset shows 100% agreement on all 5 dimensions — explained (same author wrote both sides from the same rules) and **proven not to be an engine defect** via 4 hand-constructed synthetic mismatch tests that force and correctly detect disagreement
- [x] 12/12 new tests passing on first run (no bugs this time); full suite 94/94 passing
- [x] Decision log updated: D-040 through D-043
- [x] `docs/11_comparison_engine.md` written
- [x] **Real bug caught on your machine**: `python -m autopilot_shadow.comparison.build_comparison` failed with `ModuleNotFoundError` — pytest only worked because each test file manually patches `sys.path`, the package was never actually installed. Fixed with `pyproject.toml` (D-044) — one-time `pip install -e .` and it's fixed for every day going forward, not just Day 9

## Deliverables committed
- `src/autopilot_shadow/comparison/__init__.py`
- `src/autopilot_shadow/comparison/engine.py`
- `src/autopilot_shadow/comparison/agreement.py`
- `src/autopilot_shadow/comparison/build_comparison.py`
- `pyproject.toml` (new — enables `pip install -e .`)
- `results/day09_comparisons.json`
- `results/day09_agreement_scores.json`
- `tests/test_comparison_day9.py`
- `docs/11_comparison_engine.md`
- `docs/02_decision_log.md` (updated)
- `daily_log/day09.md`

## Proof
```
$ pip install -e .

$ python -m pytest tests/test_comparison_day9.py -v
12 passed in 0.06s

$ python -m pytest tests/ -q
94 passed in 0.28s

$ python -m autopilot_shadow.comparison.build_comparison
Compared 12 resumes.
Agreement dimensions (separate, not combined):
  action_agreement     74/74  rate=1.0
  data_agreement        24/24  rate=1.0
  decision_agreement    30/30  rate=1.0
  tool_agreement        68/68  rate=1.0
  outcome_agreement     12/12  rate=1.0

Outcome disagreements: 0
```
Add screenshot: `daily_log/day09_test_output.png`
Add screenshot: `daily_log/day09_github_repo.png`

## Open items carried forward
- D-009: exact Groq model — pin when an LLM call is first actually needed
- Day 10 replaces the Day 8 placeholder confidence model with Section 10's full weighted risk model, and can use this comparison engine's dimension scores as one input to a "historical agreement" factor
- Day 13's readiness assessment reads `results/day09_agreement_scores.json` and must carry forward the same honest "synthetic data, same-author caveat" rather than presenting 100% as real-world evidence

## Notes
No bugs were caught in Day 9's own new code this time (the 12 tests passed on the first run) — a change from Days 5, 7, and 8. The real engineering effort here went into deliberately proving a negative: that a comparison engine returning 100% agreement is telling the truth about this dataset, not silently rubber-stamping everything. That's what the 4 synthetic mismatch tests are for.
