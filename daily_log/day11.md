# Day 11 — Disagreement, exception handling, approval gates

## Done
- [x] `exceptions/detector.py` — Section 17's exact rule (confidence < threshold OR required_data_missing OR conflicting_information_detected -> HUMAN_REVIEW), hard failures take priority over the new soft confidence trigger
- [x] `exceptions/disagreement.py` — Section 16's disagreement record, built from Day 9's comparison + Day 10's risk score (not recomputed), plus a short rule-based `potential_reason` guess
- [x] `exceptions/approval_gate.py` — Section 18's exact 4-state gate (APPROVE/EDIT/REJECT/ESCALATE), split so only one function (`apply_decision`, always requiring an explicit decision argument) can ever resolve a PENDING case
- [x] **Structural proof, not just a docstring claim**: AST-parsed tests confirm (a) `disagreement.py` has no import path to anything that writes human data, and (b) the string `"approved"` only ever appears inside `apply_decision`'s own function body — nothing upstream can silently approve anything
- [x] `exceptions/build_investigation.py` — runs all three over the real Day 8-10 data
- [x] 21/21 new tests passing on the first run (no bugs this time); full suite 129/129 passing
- [x] Decision log updated: D-050 through D-054
- [x] `docs/13_disagreement_exceptions_approval.md` written

## Deliverables committed
- `src/autopilot_shadow/exceptions/__init__.py`
- `src/autopilot_shadow/exceptions/detector.py`
- `src/autopilot_shadow/exceptions/disagreement.py`
- `src/autopilot_shadow/exceptions/approval_gate.py`
- `src/autopilot_shadow/exceptions/build_investigation.py`
- `results/day11_exceptions.json`
- `results/day11_disagreements.json`
- `results/day11_approval_queue.json`
- `tests/test_exceptions_day11.py`
- `docs/13_disagreement_exceptions_approval.md`
- `docs/02_decision_log.md` (updated)
- `daily_log/day11.md`

## Proof
```
$ python -m pytest tests/test_exceptions_day11.py -v
21 passed in 0.08s

$ python -m pytest tests/ -q
129 passed in 0.42s

$ python -m autopilot_shadow.exceptions.build_investigation
Exceptions detected: 6 / 74 AI-proposed events
  shadow_res_0004    classify_candidate         trigger=low_confidence         -> Confidence 0.40 is below the 0.70 review threshold.
  shadow_res_0007    classify_candidate         trigger=low_confidence         -> Confidence 0.40 is below the 0.70 review threshold.
  shadow_res_0008    classify_candidate         trigger=low_confidence         -> Confidence 0.40 is below the 0.70 review threshold.
  shadow_res_0009    extract_resume             trigger=hard_failure           -> Step failed: Resume 'res_0009' is missing fields: ['experience_years']
  shadow_res_0010    extract_resume             trigger=hard_failure           -> Step failed: Resume 'res_0010' has a malformed 'skills' field.
  shadow_res_0012    classify_candidate         trigger=low_confidence         -> Confidence 0.40 is below the 0.70 review threshold.

Disagreement records: 0 (Day 9 found 0 real mismatches — see docs/13 for why)

Approval queue: 16 / 74 proposed actions need a gate
  approval_required        10
  automate_with_monitoring 4
  human_review             2
```
Add screenshot: `daily_log/day11_test_output.png`
Add screenshot: `daily_log/day11_github_repo.png`

## Open items carried forward
- D-009: exact Groq model — pin when an LLM call is first actually needed
- Day 12 (correction memory, workflow versioning) reads `results/day11_disagreements.json` directly as its "Stored Correction Data" source, plus whatever `apply_decision` outcomes get recorded going forward
- `conflicting_information_detected` trigger is implemented and tested but never fires on the real dataset — no demonstration was ever generated with genuinely conflicting information; flagged honestly rather than hidden

## Notes
No real bugs this time — all 21 new tests passed on the first run. The engineering effort went into two structural (AST-based) proofs rather than runtime fixes: that the disagreement module literally cannot reach anything that writes human data, and that nothing except one explicitly-human-triggered function can ever mark a case "approved." Same discipline as Day 8's send_email-unreachability proof and Day 6's extraction-independence proof — a safety claim backed by parsing the actual source, not a comment.
