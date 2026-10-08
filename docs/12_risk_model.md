# 12 — Confidence and Risk Scoring (Day 10)

## 1. What this component does — Section 10

Section 10 asks for a risk model built from named factors — reversibility,
external impact, financial impact, privacy sensitivity, uncertainty,
confidence, historical human agreement, potential harm, required
authorization — explicitly warning **not to use arbitrary weights
without justification**, and to generate real numbers from real
experiments rather than copy the brief's own illustrative table.

This is also where two threads deliberately left open in earlier days
get resolved:

- Day 7's `risk_profile.py` was explicitly a small placeholder
  (reversibility + external-facing only), documented as "Day 10 will
  replace this."
- Day 9's comparison engine measures historical agreement, but only at
  dataset level — Day 10 needs it broken down **per action**.
- D-033 (Day 7) is an honest finding that res_0001 (a clean match) and
  res_0004 (a genuinely ambiguous case) halt at the *same step* under
  Day 7's per-step classification, because that classifier only looks
  at the step, not the individual case. Resolving that was explicitly
  deferred to Day 10's per-case scoring — see Section 7 of this doc.

## 2. Two kinds of factors, two files

Of Section 10's 8 named factors, four are properties of the **action
itself** and never change case to case (sending an interview email is
always irreversible and external, whether the candidate is a strong or
weak match). The other two usable here (confidence, historical
agreement) are properties of a **specific case**. Splitting the model
this way keeps each piece testable on its own:

- `risk/risk_factors.py` — the 4 static per-action factors
  (reversibility, external-facing, financial impact, privacy
  sensitivity), each with a written justification, combined into one
  `impact_score` (plain average — see Section 4 below for why plain,
  not weighted, at this level).
- `risk/historical_agreement.py` — reuses Day 9's real comparison
  output but aggregates it **per action** instead of across the whole
  dataset, because "how often has the AI agreed with the human on THIS
  kind of step" is the actual signal a risk model needs.
- `risk/risk_model.py` — combines both of the above with this case's
  own confidence (Day 6/8) into one risk score and recommendation.

## 3. The formula (documented, not arbitrary)

```
risk_score = 0.5 * impact_score + 0.3 * uncertainty + 0.2 * disagreement

impact_score  — static per-action factors (risk_factors.py)
uncertainty   = 1 - confidence                    (this case's AI confidence)
disagreement  = 1 - historical_agreement_rate(action)   (Day 9, per action)
```

**Why these weights:** `impact_score` gets the largest share (0.5)
because it reflects what the action itself could do if it goes
wrong — independent of how confident the model happens to feel about
one case; Section 22's safety framing treats impact as the thing that
must never be diluted away by a confident-sounding model. `uncertainty`
(0.3) is the genuine case-specific signal — how well does this case
actually fit the rules Day 6 extracted? `disagreement` gets the
smallest weight (0.2) **deliberately**: Day 9 documented that this
project's historical-agreement number is inflated (the human policy and
the AI logic were written by the same author from the same rules), so
giving it equal or higher weight would let an artificially perfect
number pull risk scores down further than the evidence actually
supports.

These weights are a documented starting point. Section 10 itself says
the formula must be defined and justified, not asserted as final — Day
15's experiments (A-E) and ablations (A-E) are where different weights
would get real comparative evidence behind them.

## 4. Two hard overrides that no formula is allowed to talk down

**Section 22 safety override.** An irreversible + external-facing
action (`send_interview_invitation` is the only one in this workflow)
always gets `risk_score = 1.0`, recommendation `approval_required`,
regardless of confidence or historical agreement — confirmed directly
with `test_irreversible_external_action_always_forced_to_approval_required`,
which feeds the override a near-perfect confidence (0.999) and perfect
agreement (1.0) and checks it still can't talk the score down. This
matches Day 7's own Criterion 1 and Section 22's "never allow... without
explicit approval."

**Failed-step override.** Day 8's shadow executor logs
`confidence=0.99` on `extract_resume` even when that exact call
*failed* (res_0009, res_0010) — 0.99 is the fixed "deterministic
computation" confidence, describing how much judgment the step
involves, not whether it actually succeeded. Scoring a failed step by
its nominal confidence would treat "we don't even have usable data" as
a high-confidence automate case — backwards. A `result == "failure"`
check forces `risk_score = 1.0`, `human_review` before the formula ever
runs.

## 5. A real bug caught while building this, and one caught while testing it

**In the formula's data wiring**, nothing broke — the design held up on
the first real run. **In the test suite itself**, one assertion was
wrong: `test_real_data_send_interview_invitation_always_approval_required`
asserted exactly 8 `send_interview_invitation` events in the real
shadow run, with a comment guessing it should exclude the 4
human-review cases on top of the 2 failures. Running it immediately
failed with `10 == 8` — Day 8's `ShadowExecutor` never halts (D-034),
so it logs this step (even as an explicit no-op) for **every** resume
that reaches it, not just the ones that were actually shortlisted; only
the 2 structurally-failed resumes (res_0009, res_0010) never reach it
at all. 12 − 2 = 10. Fixed the assertion to 10, with a comment
explaining why, and reran — all 14 Day 10 tests pass, full suite stays
green. This is the same category of mistake Day 9's own design doc
warned about (logging-granularity asymmetry), just surfacing in a test
comment instead of production code this time — a reminder to verify a
guessed count against the real data rather than trust the arithmetic in
a comment.

## 6. Result — generated by running the real code (S7)

```
$ python -m autopilot_shadow.risk.build_risk_scores
Scored 74 AI-proposed actions across 74 shadow events.

Recommendation counts:
  automate                 58
  approval_required        10
  automate_with_monitoring 4
  human_review             2
```

- **automate (58)** — the 6 low-impact, high-confidence steps
  (fetch/extract/check/compare/classify-clean/update) across the 10
  resumes that complete the workflow normally
- **approval_required (10)** — every `send_interview_invitation`
  proposal, on every resume that reaches it (the hard Section 22
  override, not a confidence judgment)
- **automate_with_monitoring (4)** — `classify_candidate` for
  res_0004/0007/0008/0012, where Day 6's extracted rule is UNKNOWN
  (confidence 0.40) — the exact cases D-033 flagged as needing a finer
  distinction than Day 7 could give them
- **human_review (2)** — `extract_resume` for res_0009/0010, the
  structural failures (missing/malformed source documents)

Files written: `results/day10_risk_scores.json` (74 scores, one per
shadow event), `results/day10_historical_agreement_by_action.json`
(Day 9's per-action breakdown).

## 7. D-033 resolved

```python
clean_case     = score_case("classify_candidate", "res_0001", confidence=0.95, ...)
ambiguous_case = score_case("classify_candidate", "res_0004", confidence=0.40, ...)

clean_case.risk_score      # 0.14 -> "automate"
ambiguous_case.risk_score  # 0.30 -> "automate_with_monitoring"
```

Both cases halt at the identical step under Day 7's per-step
classifier. Day 10's per-case score now tells them apart, using exactly
the mechanism D-033 deferred to this day: this case's own confidence,
not just which step it is.

## 8. Test coverage (proof)

`tests/test_risk_model_day10.py` — 14/14 passing:

```
$ python -m pytest tests/test_risk_model_day10.py -v
14 passed in 0.05s

$ python -m pytest tests/ -q
108 passed in 0.34s
```

Covers: every workflow action has defined risk factors (guards against
a future day adding an action and forgetting this file);
`impact_score`'s arithmetic for 3 hand-picked actions, including proof
that `send_interview_invitation` really does score highest of all 7;
per-action agreement aggregation and its exclusion of non-evaluable
steps; both hard overrides (Section 22 safety, failed-step), each
proven to resist a deliberately favorable confidence/agreement input;
an unknown action raising instead of silently scoring; the
missing-historical-agreement fallback; the formula's exact arithmetic
hand-checked for one case; the D-033 resolution; and three checks
against the real 74-event dataset (scores every event without
crashing, every `send_interview_invitation` forced to
`approval_required`, every failed extraction forced to `human_review`).

## 9. What Day 11 builds on top of this

Day 11 (disagreement and exception handling, approval gates) reads
`results/day10_risk_scores.json` directly: a case's `recommendation`
here is what decides whether it needs an approval gate at all, and
Section 16's disagreement-investigation record pulls this model's
`risk_score` and `reason` fields straight in, rather than recomputing
risk from scratch.
