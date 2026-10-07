# 11 — Human-AI Comparison Engine (Day 9)

## 1. What this component does — Sections 13-14

Section 13 asks for a side-by-side table: for every step, **HUMAN
ACTION vs. AI-PROPOSED ACTION**, with a match/mismatch call, confidence,
evidence and an explanation. Section 14 asks for a measurable agreement
system across **five separate dimensions** — action, data, decision,
tool, outcome — explicitly warning not to collapse everything into one
number. This is the COMPARE step in the brief's pipeline (OBSERVE →
RECONSTRUCT → PROPOSE → SHADOW RUN → **COMPARE** → APPROVE → AUTOMATE),
and it's the first thing in the whole project that actually looks at
the human trace (Day 4) and the AI trace (Day 8) *together*.

## 2. The real difficulty: the two traces don't look alike on paper

Human events (Day 4, real mock-tool calls) and AI shadow events (Day 8,
proposals only) describe the same underlying action but with different
field names and different logging habits, because one of them actually
changed state and the other deliberately never does:

- `update_candidate_record`: human events carry `status`; AI events
  carry `would_set_status`, because nothing was really written.
- `send_interview_invitation`: human events use `status == "sent"`; AI
  events use `would_send == True`.
- **Logging granularity differs.** Day 4's human policy only logs a
  `send_interview_invitation` event *at all* if the candidate was
  shortlisted — a rejected candidate's human trace is 6 events long and
  simply stops. Day 8's shadow executor always walks the full graph and
  logs this step even as an explicit no-op — a rejected candidate's AI
  trace is 7 events long. Comparing event *counts* naively would flag
  every single rejected case as "AI did something extra" — a false
  signal, not a real disagreement.
- **Failures compare on empty output.** When `extract_resume` fails
  (res_0009, res_0010 — missing/malformed source documents), both
  sides' `output` dict is `{}`. Comparing those dicts directly would
  register as a trivial, meaningless "match" with zero real evidence
  behind it.

`comparison/engine.py`'s `_normalize_step_value` handles the first two
with an explicit per-action mapping into a small canonical shape;
`_align_steps` handles the granularity asymmetry by name (treating
"AI proposed a no-op the human never bothered recording" as
outcome-equivalent, not a mismatch, while still recording
`human_present`/`ai_present` so the asymmetry stays visible, not
hidden); and the failure case is handled by comparing `exception_type`
instead of the empty `output` — did both sides fail **for the same
reason**, which is the actual meaningful question.

## 3. Five dimensions, kept separate (Section 14)

`comparison/agreement.py`'s `DimensionScore` is computed independently
per dimension and never merged:

| Dimension | Computed from | Only counted when |
|---|---|---|
| ACTION AGREEMENT | every aligned step | the step is present on at least one side |
| DATA AGREEMENT | `fetch_resume`, `extract_resume` | step present on **both** sides |
| DECISION AGREEMENT | `check_experience`, `compare_skills`, `classify_candidate` | step present on **both** sides |
| TOOL AGREEMENT | `application` field on both events | step present on **both** sides |
| OUTCOME AGREEMENT | final classification + real-vs-proposed email, computed once per resume | always (1 per resume) |

`score_dataset` rolls these up across all 12 resumes but **still
returns five separate dicts** — there is no `overall_score` or
`combined_score` field anywhere in the output. A structural test
(`test_dimensions_are_never_collapsed_into_one_number`) enforces this
directly against the output shape, not just the docstring.

## 4. The honest finding — and why it isn't a bug

Run against the real 12-resume dataset, **all five dimensions score
100%** (`results/day09_agreement_scores.json`): 74/74 action, 24/24
data, 30/30 decision, 68/68 tool, 12/12 outcome.

This looks suspicious — a comparison engine that always reports "match"
would look exactly like this. But it's a genuine, explainable property
of this dataset, not an engine defect: **the human demo policy
(`logger/human_demo.py`, Day 4) and the AI's automation/shadow logic
(`generator/handlers.py` + `shadow/shadow_handlers.py`, Days 7-8) were
both written by the same author from the same underlying business
rules** (the job description's explicit thresholds, the skill-match
tiers, the injection-override case). There was never an independent
human decision-maker in this project — it's fully synthetic data built
to exercise the pipeline end to end. A 100% agreement figure here means
"our synthetic AI logic matches our synthetic human-policy logic,"
*not* "a real AI matches a real human's judgment." Section 15's
readiness assessment (Day 13) will need to state this limitation
plainly rather than present 100% as evidence of real-world readiness.

**To prove the comparison mechanism itself isn't just hard-coded to
report "match"**, four hand-constructed synthetic test cases force
disagreement and check that the engine catches it:

- a decision mismatch (human=shortlist, AI=reject) → `decision_agreement`
  drops to 0.0, independent of other dimensions
- a tool mismatch (different `application` used for the identical
  action) → `tool_agreement` drops to 0.0 while `action_agreement` for
  that same step stays 1.0 — proving the dimensions really are
  independent, not internally conflated
- a data-extraction mismatch (different `experience_years` extracted)
  → `data_agreement` drops to 0.0
- a 2-resume mixed dataset (one full match, one full decision
  mismatch) → the dataset-level rollup is exactly 0.5, and the
  mismatched resume appears in `outcome_disagreements`

All four pass, which is the real evidence that the 100% figure on the
actual dataset reflects the data, not the measuring instrument.

## 5. Result — generated by running the real code (S7)

```
$ python -m autopilot_shadow.comparison.build_comparison
Compared 12 resumes.
Agreement dimensions (separate, not combined):
  action_agreement     74/74  rate=1.0
  data_agreement        24/24  rate=1.0
  decision_agreement    30/30  rate=1.0
  tool_agreement        68/68  rate=1.0
  outcome_agreement     12/12  rate=1.0

Outcome disagreements: 0

Wrote: results/day09_comparisons.json, results/day09_agreement_scores.json
```

## 6. Test coverage (proof)

`tests/test_comparison_day9.py` — 12/12 passing:

```
$ python -m pytest tests/test_comparison_day9.py -v
12 passed in 0.06s

$ python -m pytest tests/ -q
94 passed in 0.28s
```

Covers: `demo_id`→`resume_id` parsing for both sources, including
correct exclusion of Day 4's artificial `demo_dup_*`/`demo_fault_*`
demos (D-022's same reasoning applied here); all 12 resumes compared;
the full-agreement honest finding on real data, with its own docstring
explaining why that's expected, not suspicious; the
`send_interview_invitation` logging-asymmetry handled as a match, not a
false mismatch (res_0002); identical exception failures correctly
compared on `exception_type` (res_0009); and the four synthetic
mismatch tests described above, proving the engine detects real
disagreement across every dimension plus the dataset-level rollup math.

## 7. What Day 10 builds on top of this

Day 10 replaces the placeholder confidence model (`shadow/confidence.py`,
Day 8) with Section 10's full weighted risk model (reversibility,
external impact, financial impact, privacy sensitivity, historical
agreement — this comparison engine's dimension scores become one input
to "historical agreement"). Day 13's readiness assessment will also
read `results/day09_agreement_scores.json` directly, carrying forward
this same honest "synthetic data, not real-world" caveat rather than
treating 100% as a finished result.
