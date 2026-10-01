# Day 6 — Decision and condition extraction

## Done
- [x] Decision extraction engine, reading only `demonstrations.json` + `job_description.json` — no dependency on Day 4's generator logic (`decisions/extraction.py`)
- [x] Mandatory 3-way rule labelling implemented: explicit / inferred / unknown (Section 8)
- [x] Explicit rules traced directly to JD config (experience threshold, full skill match)
- [x] Honest finding: zero rules reached "inferred" — every edge case had only 1 supporting example, correctly reported as unknown rather than fabricated confidence
- [x] Prompt-injection case specifically flagged as unknown from the engine's point of view, documented as an open design question
- [x] Rules attached to Day 5's reconstructed workflow, saved as `data/workflow_with_decisions.json`
- [x] 9/9 new tests passing; full suite 59/59 passing
- [x] Decision log updated: D-025 through D-028
- [x] `docs/08_decision_extraction.md` written

## Deliverables committed
- `src/autopilot_shadow/decisions/extraction.py`
- `src/autopilot_shadow/decisions/build_rules.py`
- `src/autopilot_shadow/decisions/__init__.py`
- `data/workflow_with_decisions.json`
- `results/day06_decision_extraction.json`
- `tests/test_decision_extraction_day6.py`
- `docs/08_decision_extraction.md`
- `docs/02_decision_log.md` (updated)
- `daily_log/day06.md`

## Proof
```
$ python -m pytest tests/test_decision_extraction_day6.py -v
9 passed in 0.11s

$ python -m pytest tests/ -v
59 passed in 0.16s

$ python -m autopilot_shadow.decisions.build_rules
Extracted 6 rules: {'explicit': 2, 'inferred': 0, 'unknown': 4}
```
Add screenshot: `daily_log/day06_test_output.png`
Add screenshot: `daily_log/day06_github_repo.png`

## Open items carried forward
- D-004: Executor (LangGraph vs custom DAG) — decide Day 7
- D-009: exact Groq model — pin when an LLM call is first actually needed
- Open design question from Day 6: should prompt-injection handling become explicit, declared policy rather than implicit? (candidate for Day 11, exception detection)
- Day 13 readiness scoring must reflect that ambiguous cases currently have "unknown" rule backing, not artificially high confidence

## Notes
