# 15 — Automation-Readiness Evaluation (Day 13)

## 1. What this component does — Sections 15, 26, 27, 28, 29

This is the project's actual answer to the question the whole system
exists to ask: **"Is this workflow ready for partial or full
automation?"** Four pieces, all built on real numbers already generated
by Days 5-12, nothing recomputed from scratch except two genuinely new
cross-file questions (false automation/escalation rate):

- **Section 15 — Shadow Score**: one headline number, but decomposable.
- **Section 26 — Readiness decision**: one of 4 categories.
- **Sections 27/28 — Evaluation metrics**: reconstruction accuracy,
  decision-extraction quality, human-AI agreement, risk/reversibility.
- **Section 29 — the critical metric**: false automation rate,
  explicitly prioritized above raw automation coverage.

## 2. The Shadow Score formula (Section 15)

```
shadow_score = 100 * mean(accuracy, human_agreement,
                           decision_stability, evidence_coverage)
```

Equal weights (0.25 each) — the same justification Day 10 gave for
`impact_score`'s plain average (D-045/D-046): these four measure
genuinely different things, and this project has no comparative
experiment yet (that's Day 15) to justify weighting one over another.
Risk and Reversibility are reported **alongside** the score as
categorical fields, exactly matching the brief's own example table —
they are safety context, not success metrics, so they are not folded
into the average.

**Hard cap, mirroring Day 10's override pattern (D-047):** if Section
29's false_automation_rate is ever observed above 0, the score is
capped at 49/100 regardless of what the other four components say — a
formula cannot average away an observed false automation.

## 3. Two genuinely new metrics: false automation and false escalation

**False automation rate (Section 29, the critical metric):** of every
case Day 10 recommended `"automate"`, how many did *not* match the
human's actual decision (per Day 9)? Neither Day 9 nor Day 10 alone
answers this — it requires cross-referencing both by
`(resume_id, action)`. Real result: **0.0** (0 of 58 evaluated).

**False escalation rate (Section 28's companion metric):** of the
*discretionary* gated cases — `automate_with_monitoring` only, where
low AI *confidence* (not hard policy) drove the gate — how many would
have matched the human anyway if fully automated? `human_review`
(structural failures) and `approval_required` (Section 22's hard
safety override) are deliberately **excluded** from this metric: gating
those is correct by policy no matter how the AI's guess would have
turned out, so counting them would misrepresent policy-driven caution
as wasted caution. Proven by
`test_false_escalation_rate_excludes_policy_gated_cases`.

**Honest finding:** real result is **1.0** — all 4 discretionary
"monitor" cases (confidence 0.40, UNKNOWN-rule `classify_candidate`)
would have matched the human decision anyway in this dataset.

**How to read that, and how not to:** this is a real, computed number,
not invented — but it comes from only 4 cases, in a dataset where the
human policy and the AI logic share the same author (Day 9/D-043, Day
11/D-054). It is *not* general evidence that this system is
"over-cautious" and should automate more; it is a narrow, honest
observation about this specific 12-resume dataset, stated plainly
rather than spun into a stronger claim than the evidence supports
(Section 38).

## 4. The readiness decision (Section 26) — and why HIGH is structurally blocked

`readiness_decision.py`'s ordered logic:

1. Any observed false automation → **NOT_READY**, unconditionally
   (Section 29's own priority).
2. `evidence_coverage < 0.25` → **NOT_READY** (too much of the decision
   logic rests on single-example UNKNOWN rules).
3. `evidence_coverage >= 0.85` **AND** `independent_evaluation=True` →
   **HIGH_AUTOMATION_READINESS**.
4. Otherwise, if Day 11's approval gates are operational (they are,
   tested, 21/21 passing) → **HUMAN_IN_THE_LOOP_READY**.
5. Fallback → **PARTIALLY_READY**.

**`independent_evaluation` is a hard gate, not a number**, and it is
hard-coded `False` in this codebase. This project's human-agreement
figures come from a human policy and an AI implementation written by
the *same author* from the *same rules* — there has never been a real,
independently-sourced human decision for this system to be checked
against. Claiming "high automation readiness" from numbers that cannot
tell real agreement apart from shared-authorship coincidence would be
exactly the kind of overclaimed confidence Section 38 forbids. This
gate stays `False` until real human decisions exist to evaluate
against — flipping it is a project decision, not a metric that creeps
upward on its own.

**Real result**: evidence_coverage=0.333 (above the NOT_READY floor,
below the HIGH floor), false_automation_rate=0.0, gates operational →
**HUMAN_IN_THE_LOOP_READY**. This also directly answers Day 12's
deferred V4 question: "High-Confidence Automation" is **not yet
justified** by real evidence — exactly the honest, unforced conclusion
V4 was left open for.

## 5. Result — generated by running the real code (S7)

```
$ python -m autopilot_shadow.readiness.build_readiness
SHADOW SCORE: 74.24 / 100

Decomposed (Section 15 — never read the headline number alone):
  accuracy               1.0
  human_agreement        1.0
  decision_stability     0.6364
  evidence_coverage      0.3333
  risk                   low
  reversibility          high

Section 29 — CRITICAL METRIC — false_automation_rate: 0.0 (0 / 58 automate cases)
Companion — false_escalation_rate (discretionary gates only): 1.0 (4 / 4 monitored cases)

READINESS DECISION (Section 26): HUMAN_IN_THE_LOOP_READY
  No false automation observed; low-risk steps automate directly; Day 11's tested approval gates
  (Section 18) let the AI prepare every other decision for human approval. evidence_coverage=0.3333
  is not yet high enough, or human-agreement data is not yet independently sourced
  (independent_evaluation=False), for the HIGH tier.

Wrote: results/day13_readiness_assessment.json
```

Note `accuracy=1.0` and `human_agreement=1.0` are both carried forward
with their own established caveats (Day 5 reconstructs synthetic data
built from its own known schema; Day 9's agreement is same-author data)
— the Shadow Score does not hide these, it inherits and is constrained
by them, which is exactly why `decision_stability` and
`evidence_coverage` (the two numbers NOT inflated by those caveats) are
what actually keeps the score at 74 instead of near 100, and what keeps
the readiness tier at HUMAN_IN_THE_LOOP_READY instead of HIGH.

## 6. Test coverage (proof)

`tests/test_readiness_day13.py` — 17/17 passing on the first run:

```
$ python -m pytest tests/test_readiness_day13.py -v
17 passed in 0.07s

$ python -m pytest tests/ -q
168 passed in 0.43s
```

Covers: every metric's real value hand-checked against its source file
(reconstruction accuracy, decision-extraction coverage/stability, Day 9
agreement mean, risk/reversibility labels); false automation rate on a
hand-built mismatched case, and the real 0.0 result; false escalation
rate's exclusion of policy-gated cases proven structurally, and the
real 1.0 finding; the Shadow Score's real component values and its hard
cap (forced via a monkeypatched false-automation result, since the real
dataset has none to trigger it); every branch of the readiness decision
(false automation, low coverage, the HIGH tier's dual requirement
proven to fail without `independent_evaluation=True` even at high
coverage, human-in-the-loop vs. partially-ready depending on gate
status); the `INDEPENDENT_EVALUATION` constant's current honest value;
and the full real-data pipeline landing on `HUMAN_IN_THE_LOOP_READY`.

## 7. What Day 14 builds on top of this

Day 14 (failure scenarios + dashboard) surfaces
`results/day13_readiness_assessment.json` directly on the dashboard —
the Shadow Score, its decomposition, and the readiness tier are the
project's actual headline output, not something Day 14 recomputes.
