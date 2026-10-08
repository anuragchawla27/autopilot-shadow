# Day 10 — Confidence and risk scoring

## Done
- [x] `risk/risk_factors.py` — Section 10's 4 static per-action factors (reversibility, external-facing, financial impact, privacy sensitivity), each hand-justified, combined into `impact_score`
- [x] `risk/historical_agreement.py` — Day 9's comparisons reaggregated PER ACTION (not just dataset-wide)
- [x] `risk/risk_model.py` — the documented weighted formula (`0.5*impact + 0.3*uncertainty + 0.2*disagreement`) plus two hard overrides: Section 22 safety (irreversible+external always `approval_required`) and failed-step (never scored by nominal confidence)
- [x] `risk/build_risk_scores.py` — runs the model over the real 74-event shadow run
- [x] **D-033 (Day 7's deferred finding) resolved**: res_0001 (clean match) and res_0004 (ambiguous) halt at the same step under Day 7's classifier but now get genuinely different risk scores/recommendations via per-case confidence
- [x] **Real bug caught by running the tests**: a test asserted the wrong count of `send_interview_invitation` events (8 instead of 10) — fixed, with the actual reasoning (ShadowExecutor never halts, D-034) written into the test comment
- [x] 14/14 new tests passing after the fix; full suite 108/108 passing
- [x] Decision log updated: D-045 through D-049
- [x] `docs/12_risk_model.md` written

## Deliverables committed
- `src/autopilot_shadow/risk/__init__.py`
- `src/autopilot_shadow/risk/risk_factors.py`
- `src/autopilot_shadow/risk/historical_agreement.py`
- `src/autopilot_shadow/risk/risk_model.py`
- `src/autopilot_shadow/risk/build_risk_scores.py`
- `results/day10_risk_scores.json`
- `results/day10_historical_agreement_by_action.json`
- `tests/test_risk_model_day10.py`
- `docs/12_risk_model.md`
- `docs/02_decision_log.md` (updated)
- `daily_log/day10.md`

## Proof
```
$ python -m pytest tests/test_risk_model_day10.py -v
14 passed in 0.05s

$ python -m pytest tests/ -q
108 passed in 0.34s

$ python -m autopilot_shadow.risk.build_risk_scores
Scored 74 AI-proposed actions across 74 shadow events.

Recommendation counts:
  automate                 58
  approval_required        10
  automate_with_monitoring 4
  human_review             2
```
Add screenshot: `daily_log/day10_test_output.png`
Add screenshot: `daily_log/day10_github_repo.png`

## Open items carried forward
- D-009: exact Groq model — pin when an LLM call is first actually needed
- Day 11 reads `results/day10_risk_scores.json` directly — a case's `recommendation` here decides whether it needs an approval gate, and Section 16's disagreement record pulls this model's `risk_score`/`reason` straight in
- The formula's weights (0.5/0.3/0.2) are documented as a starting point, explicitly flagged for revisiting once Day 15's experiments (A-E) and ablations (A-E) exist to justify different ones with real comparative evidence

## Notes
One real bug this time, caught in the test suite rather than the production code: a hand-written comment guessed the wrong count of `send_interview_invitation` events in the real dataset (8 instead of 10), because it forgot Day 8's shadow executor logs that step as a no-op for every resume, not just the shortlisted ones. Running the test instead of trusting the comment's arithmetic caught it immediately — the same discipline every prior day has relied on.
