# 10 — Shadow Execution (Day 8)

## 1. What this component does — the brief's central feature

Section 12 opens: "This is the central feature." In shadow mode, the AI
performs the same reasoning a human would, for the same case, and
records what it would have done — but never performs an irreversible
external action. Section 2 frames the whole project around this:
OBSERVE → RECONSTRUCT → PROPOSE → **SHADOW RUN** → COMPARE → APPROVE →
AUTOMATE. Everything through Day 7 built toward being able to run this
one step safely.

## 2. Why shadow mode can't reuse Day 7's executor directly

Day 7's `AutomationExecutor` HALTS at the first `HUMAN_REVIEW`/`BLOCKED`
step, because it's deciding what to actually *execute* — stopping there
is correct and required (Safety S3). Shadow mode's job is different: it
must keep reasoning through **every** step for every case, because it
never executes anything for real — there's nothing to stop and wait for
a human about. `ShadowExecutor` is a new, smaller executor built for
this: no halting, ever; instead, every step is converted to a *proposal*.

## 3. Three real bugs caught by actually running the code

I want to be upfront about these, because each one would have silently
produced wrong, misleading output if I'd only read the code instead of
running it against the real 12-resume dataset.

### Bug 1 — confidence computation used mismatched field names (D-038)

The first version of the confidence matcher compared `case_evidence.get(field) == value`, field by field. But Day 6's explicit rules use real field names with real operators (`experience_years < 2`, `required_skills_present == True`), while I was passing a context dict with *different* field names (`experience_ok`, `skill_match_tier`) and ignoring the operator entirely. Result: **every single case fell through to "no matching rule," confidence 0.3 — even res_0001, a textbook clean match.**

Fixed by building a proper, operator-aware rule evaluator
(`common/rule_evaluation.py`) and a case context that includes every
field any rule might reference.

### Bug 2 — shadow mode drafted interview emails for rejected candidates (D-036)

The first version of `shadow_send_interview_invitation` drafted an
email unconditionally, regardless of the classification made earlier in
the same run. Running the full 12-resume batch immediately showed
`res_0002` (a clear reject) outputting "AI would send an interview
invite" — which is simply wrong, and would have fed Day 9's comparison
engine a spurious disagreement that isn't really about communication at
all.

Fixed: the handler now checks `ctx["classification"] == "shortlist"`
first, matching Section 4's own framing ("Communication decision" is
conditional on a shortlist outcome).

### Bug 3 — confidence picked the wrong rule when two rules both matched (D-037)

After fixing Bug 1, I inspected the real output line by line rather than
trusting the summary numbers, and found `res_0012` (the prompt-injection
resume, which also happens to have a full skill match) reporting 0.95
confidence — the *explicit, high-confidence* number — for a decision
that was actually `human_review`. What happened: this case's evidence
satisfies **two** extracted rules at once — the explicit full-match rule
(which implies `shortlist` and knows nothing about injection) and the
injection-specific unknown rule (which implies `human_review`, the
decision actually made). The matcher picked whichever rule happened to
be checked first, producing a confidently wrong number.

Fixed: confidence is now grounded in the rule that both matches the
case **and** whose `then_outcome` equals the decision actually made
(D-037). When several rules match, the one with the strongest evidence
backing is used, and any disagreement among matching rules is noted in
the explanation text rather than hidden.

## 4. Design decisions that followed from building this honestly

**A fresh environment per shadow run (D-034).** The AI and the human
are independent observers of the same resume, not one acting on the
other's state. This also sidesteps a real false-positive: re-fetching a
resume the human already fetched would otherwise trip our own
duplicate-submission detector (`resume_db.py`) — correctly built for
real duplicate requests, but wrong to apply across two separate
observers. Verified directly:
`test_shadow_run_uses_fresh_environment_no_duplicate_false_positive`.

**Nothing is ever committed, not just irreversible actions (D-035).**
Section 12 literally only requires blocking *irreversible* actions, but
I went further: `update_candidate_record` (reversible, per Day 7's own
risk profile) is also proposal-only in shadow mode. A real AI write into
the human's own CRM record — even a reversible one — would corrupt the
very human-vs-AI comparison Day 9 needs to make. "Propose, never commit"
is a simpler and stronger boundary than "only block irreversible ones."

**`send_email` is structurally unreachable from shadow code**, not just
avoided by convention — proven by parsing `shadow_handlers.py`'s AST and
confirming `send_email` never appears as a called method anywhere in the
module (`test_shadow_handlers_module_never_calls_send_email`).

## 5. Provisional confidence model (Day 10 will replace this)

`shadow/confidence.py` assigns:

| Case | Confidence | Why |
|---|---|---|
| Deterministic step (fetch/extract/check/compare) | 0.99 | Pure computation, no judgment |
| Decision backed by an EXPLICIT rule | 0.95 | Grounded in stated configuration |
| Decision backed by an INFERRED rule | 0.75 | Consistent pattern, 2+ examples |
| Decision backed by an UNKNOWN rule | 0.40 | Insufficient/contradictory evidence |
| No rule explains the actual decision | 0.30 | A case unlike anything in the 12 demos |

This is explicitly a placeholder — small, hand-justified, and designed
to be replaced, exactly like Day 7's `risk_profile.py` was. Day 10
builds the real, weighted, experiment-backed risk model (reversibility,
external impact, financial impact, privacy, historical agreement, etc.
— Section 10's full factor list).

## 6. Result — generated by running the real code (S7)

```
$ python -m autopilot_shadow.shadow.build_shadow_run
Shadow-executed 12 resumes, 74 total proposed events.
  res_0001: 7 events, last='send_interview_invitation' (success), proposed='shortlist', confidence=0.95
  res_0002: 7 events, last='send_interview_invitation' (success), proposed='reject', confidence=0.95
  res_0003: 7 events, last='send_interview_invitation' (success), proposed='shortlist', confidence=0.95
  res_0004: 7 events, last='send_interview_invitation' (success), proposed='human_review', confidence=0.4
  res_0005: 7 events, last='send_interview_invitation' (success), proposed='reject', confidence=0.95
  res_0006: 7 events, last='send_interview_invitation' (success), proposed='shortlist', confidence=0.95
  res_0007: 7 events, last='send_interview_invitation' (success), proposed='human_review', confidence=0.4
  res_0008: 7 events, last='send_interview_invitation' (success), proposed='human_review', confidence=0.4
  res_0009: 2 events, last='extract_resume' (failure), proposed=None, confidence=None
  res_0010: 2 events, last='extract_resume' (failure), proposed=None, confidence=None
  res_0011: 7 events, last='send_interview_invitation' (success), proposed='shortlist', confidence=0.95
  res_0012: 7 events, last='send_interview_invitation' (success), proposed='human_review', confidence=0.4
```

Files written: `data/shadow_run.json` (74 AI-proposed Events across 12
demos), `results/day08_shadow_run_summary.json`.

res_0009 and res_0010 correctly fail at `extract_resume` in shadow mode
too — shadow execution doesn't bypass genuine structural problems
(missing/malformed fields), it only changes what happens with
*judgment* steps.

## 7. Test coverage (proof)

`tests/test_shadow_execution_day8.py` — 12/12 passing:

```
$ python -m pytest tests/test_shadow_execution_day8.py -v
12 passed in 0.12s
```

Full suite: **82/82 passing** (Days 2-8 combined).

Covers: shadow mode runs all 7 steps without halting (unlike Day 7's
executor on the identical workflow); a real, separate CRM object proves
nothing external was ever touched; the email-sent flag is proposal-only
with the right note; the rejected-candidate email-drafting bug stays
fixed (direct regression test); an AST-based structural proof that
`send_email` is never called anywhere in the shadow handlers module; the
fresh-environment design prevents a duplicate-fetch false positive;
confidence is correctly high for explicit-rule cases and low for
unknown-rule cases; the outcome-matching fix is directly regression-
tested on res_0012; deterministic steps get fixed high confidence;
structural exceptions still halt the shadow run; and the full 12-resume
dataset build is itself exercised and checked (every resume present,
every event correctly tagged `actor_type=ai_shadow`,
`approval=not_required`).

## 8. What Day 9 builds on top of this

Day 9's comparison engine reads `data/demonstrations.json` (human
Events, Day 4) side by side with `data/shadow_run.json` (AI Events, Day
8), matched by `resume_id`, and scores agreement across five dimensions
(action, data, decision, tool, outcome) per Section 14 — never collapsed
into one number. The honest disagreement cases already visible in this
day's output (res_0004, res_0007, res_0008, res_0012 — all genuinely
ambiguous, all correctly low-confidence) are exactly the cases Day 9's
comparison should flag.
