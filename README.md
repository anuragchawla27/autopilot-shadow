# AUTOPILOT SHADOW

**AI Workflow Reconstruction, Shadow Execution & Automation-Readiness Assessment**
A 15-day Advanced AI Automation Internship project — PranavX Labs Challenge.

> Read this file top to bottom and you'll understand the whole project — what it
> does, why it's useful, how "shadow mode" works, what's automated vs. kept
> human, and how to run it yourself. No other file is required to understand
> the idea.

---

## 1. The problem, in plain words

Every business runs repetitive workflows — screening resumes, processing
refunds, routing support tickets, approving invoices. People assume "let's
just get AI to do this" is a simple switch to flip. It isn't, for two reasons:

1. **Nobody has written the workflow down properly.** It lives in a person's
   head — which steps happen, in what order, which exceptions come up, which
   decisions are "obvious" and which need judgment. You can't automate what
   you haven't actually described.
2. **Letting an AI act immediately is dangerous.** If an AI is wrong even 5%
   of the time and it's allowed to actually send the email, reject the
   candidate, or update the record — those mistakes are now real and often
   can't be undone.

**AUTOPILOT SHADOW is a system that solves both problems**, end to end, and
proves — with real, measured numbers, not promises — whether a given
workflow is actually safe to automate, and how much of it.

## 2. The business value — why this matters

If you run this system against a real company workflow, it gives you:

- **A written-down version of a process that previously only existed as
  "ask Priya, she knows how we do this."** That alone is valuable — it's
  documentation that survives when Priya leaves.
- **A concrete answer to "can we automate this?"** — not a guess, but a
  score built from real test runs, broken into readable parts (accuracy,
  agreement with humans, stability, evidence, risk) instead of one
  unexplained number someone has to trust blindly.
- **Time and cost savings**, because the parts of the workflow that are
  genuinely safe (data lookups, straightforward checks, routine record
  updates) can run without a human watching every single case — while the
  parts that carry real consequences (saying no to a person, sending an
  external message, anything that can't be undone) are still routed to a
  human, automatically.
- **A safety net before deployment**, because the system runs the proposed
  automation in **shadow mode** against real data first — so you find out
  *before* go-live whether it would have made mistakes, not after it's
  already emailed a customer.
- **An honest readiness report**, not a sales pitch. This project's own
  result for its demo workflow is a score of 74.24/100 and a tier of
  *"human-in-the-loop ready"* — one level below full automation — and it
  says exactly why it isn't higher. That's the point: a system that tells
  you the truth about its own limits is more useful than one that always
  says "yes, fully automate."

## 3. What "shadow mode" actually means (plain-language version)

Think of a new employee shadowing an experienced one on their first week.
The new person watches every case, writes down what *they* would have done,
and compares notes with the senior employee at the end of the day — but they
don't actually touch the keyboard, send the email, or make the call
themselves. Nothing they "do" is real yet.

That's exactly what this system does with AI:

- For every real case (e.g. every resume), the AI works through the whole
  workflow and decides what it *would* do at each step.
- It writes all of that down — not as a hidden log, but as a full, inspectable
  record of every proposed action.
- **It never actually sends the email, updates the real record, or takes any
  action that can't be undone.** Those steps are swapped for safe,
  no-op equivalents that only *compute and record* what would have happened.
- Afterwards, the system compares what the AI *would have done* against what
  the human actually did, case by case, and reports where they agree and
  where they don't.

Only once a workflow has been shadowed enough times, with high enough
agreement and low enough risk, does the system even recommend letting
certain steps run for real — and even then, the riskiest steps (anything
irreversible or external-facing) are *hard-coded* to always require a human,
no matter how confident the AI is. That hard rule can't be automated away,
on purpose.

## 4. Where automation is used — and where it deliberately isn't

Not every step in a workflow deserves the same treatment, and this project
does **not** automate everything just because it can. Each step is scored
individually and placed into one of 5 categories:

| Category | Meaning | Example from this project |
|---|---|---|
| `AUTOMATE` | Safe, low-impact, reversible — runs without a human | Fetching a resume, extracting fields, checking years of experience |
| `AUTOMATE_WITH_MONITORING` | Automated, but logged for periodic human spot-checks | Comparing candidate skills against requirements |
| `HUMAN_REVIEW` | AI proposes an action, a human must approve it first | Final candidate classification |
| `HUMAN_ONLY` | AI never decides this — only a human can | Judgment calls outside the AI's training data |
| `BLOCKED` | Never automated, by design, regardless of confidence | Any irreversible, externally-visible action (e.g. sending an interview invite) taken with a candidate who wasn't actually approved |

This is the honest answer to "isn't automation risky on every step?" — yes,
on some steps it genuinely is, so this project doesn't pretend otherwise.
Instead it automates the steps that are safe to automate (mechanical,
reversible, low-consequence), keeps a human in the loop for steps with real
judgment or consequences, and enforces that split with code — not just a
policy document — using two **hard overrides** that no score can bypass:

1. An irreversible action that also faces an external party (e.g. a
   candidate) always requires human approval, however confident the AI is.
2. A step that actually failed during execution is always sent to a human,
   regardless of its usual automation category.

**Measured proof this matters:** when the project ran the same 12-case
dataset through a version of itself with *no* such gates, it produced **6
unsafe interview invitations out of 12** — invites drafted for candidates
who were never actually approved. Adding only a risk/approval gate brought
that number to **0**, with the rest of the workflow still running. That's
the concrete, re-runnable evidence behind "automate only where it's safe."

## 5. How it saves manual effort and time

- A human reviewing every single case end-to-end is replaced by a human
  reviewing **only the cases and steps that actually need judgment** — the
  mechanical steps (data lookup, field extraction, straightforward
  threshold checks) run unattended because the system has evidence they're
  safe to.
- Instead of a person manually comparing "what did the AI suggest vs. what
  did we actually do" by hand, the system computes that agreement
  automatically, across five different angles (did it take the same action,
  use the same data, reach the same decision, call the same tool, get the
  same outcome) — work that would otherwise take hours of manual audit per
  batch of cases.
- Instead of finding out a workflow is unreliable *after* deploying it (and
  after it's already sent bad emails or made bad records), shadow mode
  surfaces that risk beforehand, against real data, at no real-world cost.
- The automation-readiness score and its breakdown replace a long, subjective
  debate ("do we trust this enough to turn it on?") with a specific,
  defensible answer that also says exactly what evidence is still missing.

## 6. The pipeline — nine stages, each one a checkpoint

```
OBSERVE → RECONSTRUCT → PROPOSE → SHADOW → COMPARE → LEARN → ASSESS → APPROVE → AUTOMATE
```

| Stage | What happens | Where in this repo |
|---|---|---|
| **OBSERVE** | Record humans actually performing the workflow (demonstrations) | `src/autopilot_shadow/mock_env/`, `data/demonstrations.json` |
| **RECONSTRUCT** | Turn those raw events into a structured workflow (steps, order, branches) | `src/autopilot_shadow/logger/`, `src/autopilot_shadow/reconstruction/` |
| *(decision extraction)* | Pull out the decision rules behind each step, labelled explicit / inferred / unknown — never guessed | `src/autopilot_shadow/decisions/` |
| **PROPOSE** | Classify every step by how safe it is to automate (table in §4) | `src/autopilot_shadow/generator/` |
| **SHADOW** | Run the whole thing for real on real data, but with every irreversible action swapped for a safe, recording-only version | `src/autopilot_shadow/shadow/` |
| **COMPARE** | Compare AI proposals vs. human decisions, on 5 separate dimensions | `src/autopilot_shadow/comparison/` |
| *(risk & confidence)* | Score every proposed action's risk from documented factors, with 2 hard overrides | `src/autopilot_shadow/risk/` |
| **LEARN** | Record disagreements, exceptions, and human corrections so the system keeps a memory of what it got wrong | `src/autopilot_shadow/exceptions/`, `src/autopilot_shadow/correction/`, `src/autopilot_shadow/versioning/` |
| **ASSESS** | Turn everything above into one decomposable automation-readiness score and tier | `src/autopilot_shadow/readiness/` |
| **APPROVE / AUTOMATE** | Human approval gates; only cleared, low-risk steps are recommended to run unattended | `src/autopilot_shadow/exceptions/` (approval gates), enforced throughout `shadow/` and `risk/` |

Every stage above reads only the output of the stage before it and writes a
real file under `results/` — so each stage can be re-run and checked
independently, and nothing in this README is a claim without a file backing
it up.

## 7. Repository structure

```
autopilot-shadow/
├── README.md                      ← you are here
├── requirements.txt                dependencies (pydantic, pytest, streamlit, pandas)
├── pyproject.toml                  package config (src-layout, pytest config)
│
├── src/autopilot_shadow/           the actual system — one folder per pipeline stage
│   ├── schemas/                      Event & Workflow data models (Pydantic)
│   ├── mock_env/                     synthetic tools: resume DB, CRM, email, tickets
│   ├── logger/                       turns raw demonstrations into Event logs
│   ├── reconstruction/               Events → structured Workflow
│   ├── decisions/                    decision-rule extraction (explicit/inferred/unknown)
│   ├── generator/                    step classification + the real automation executor
│   ├── shadow/                       shadow execution engine (the safety core)
│   ├── comparison/                   human-vs-AI agreement engine (5 dimensions)
│   ├── risk/                         risk/confidence scoring + hard overrides
│   ├── exceptions/                   disagreement handling, exceptions, approval gates
│   ├── correction/                   correction memory (learns from human fixes)
│   ├── versioning/                   workflow version history
│   ├── readiness/                    automation-readiness scoring
│   ├── failure_scenarios/            10 forced-failure safety tests
│   ├── experiments/                  Day 15: controlled experiments + ablation study
│   └── common/                       shared utilities
│
├── dashboard/                      Streamlit app — reads results/*.json, never recomputes
│   ├── app.py
│   └── data_loader.py
│
├── data/                           synthetic input data (resumes, job description, demos)
│   ├── demonstrations.json           the 12 "human" demo runs
│   ├── resumes.json                  synthetic candidate resumes
│   ├── job_description.json
│   ├── ground_truth.json             independent answer key, used for calibration checks
│   └── *_workflow*.json              intermediate reconstructed/classified workflow states
│
├── results/                        every number in this project, as real generated JSON
│   └── dayNN_*.json                  one or more output files per day/stage — nothing hand-typed
│
├── tests/                          218 automated tests, one or more files per day
│   └── test_*_dayNN.py
│
├── docs/                           one write-up per component, plus project-wide docs
│   ├── 01_problem_scope_safety.md    the problem, workflow choice, and safety rules
│   ├── 02_decision_log.md            every real engineering decision, with reasoning
│   ├── 03_established_vs_own_design.md
│   ├── 04_...15_...                  one doc per pipeline component (Days 2-13)
│   ├── 16_failure_scenarios_dashboard.md
│   ├── 17_requirements_traceability.md   proof every brief requirement is met
│   ├── 18_experiments_and_ablation.md    Day 15 experiments + ablation results
│   └── 19_final_engineering_report.md    the full final report (Section 37 format)
│
└── daily_log/                      one entry per day, with proof of completion (day01.md … day15b.md)
```

## 8. How to clone and run it

**Requirements:** Python 3.10+, git.

```bash
# 1. Clone the repository
git clone https://github.com/anuragchawla27/autopilot-shadow.git
cd autopilot-shadow

# 2. (recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the full test suite (218 tests — proves every claim in this repo is real)
python -m pytest tests/ -q

# 5. Launch the dashboard (reads results/*.json — nothing is recomputed live)
streamlit run dashboard/app.py
```

To regenerate any stage's output yourself instead of trusting the committed
`results/*.json` files, each stage has its own runnable module, e.g.:

```bash
python -m autopilot_shadow.experiments.build_experiments   # Day 15 experiments
python -m autopilot_shadow.experiments.build_ablation       # Day 15 ablation study
```

(Every `build_*` script under `src/autopilot_shadow/<stage>/` follows the
same pattern — see the matching `docs/NN_*.md` for the exact command.)

## 9. Dashboard screenshots

> **Placeholders below — screenshots not yet added.** Run
> `streamlit run dashboard/app.py` locally, save a screenshot per tab into
> `docs/screenshots/` using the filenames below, and each image will appear
> here automatically (and can be dropped into `docs/19_final_engineering_report.md`
> and the presentation the same way).

| Tab | Screenshot |
|---|---|
| Overview | ![Dashboard — Overview](docs/screenshots/dashboard_overview.png) |
| Workflow structure | ![Dashboard — Workflow](docs/screenshots/dashboard_workflow.png) |
| Shadow run | ![Dashboard — Shadow run](docs/screenshots/dashboard_shadow_run.png) |
| Human-AI comparison | ![Dashboard — Comparison](docs/screenshots/dashboard_comparison.png) |
| Risk scores | ![Dashboard — Risk](docs/screenshots/dashboard_risk.png) |
| Corrections & versioning | ![Dashboard — Corrections](docs/screenshots/dashboard_corrections.png) |
| Automation readiness | ![Dashboard — Readiness](docs/screenshots/dashboard_readiness.png) |
| Failure scenarios | ![Dashboard — Failures](docs/screenshots/dashboard_failures.png) |
| Experiments & ablation (Day 15) | ![Dashboard — Experiments](docs/screenshots/dashboard_experiments.png) |

`docs/screenshots/` does not exist yet — create it and add the 9 PNGs above
(any size is fine; GitHub scales them to fit). Until then, each row above
renders as a broken-image icon on GitHub, which is expected for a
placeholder and not a bug.

## 10. The evidence, in one place

Everything below is read from a real file in `results/`, never hand-typed:

- **218/218 automated tests passing**, across every stage.
- **10/10 forced failure scenarios fail safely** (wrong extraction, wrong
  tool, overconfident-but-wrong, missing data, malformed output,
  human/AI disagreement, workflow exceptions, duplicate requests, external
  actions, high-risk actions).
- **Experiments (Section 30):** automation with no safety gates produces 6
  unsafe interview invitations out of 12 cases; the full system with its
  risk model produces 0.
- **Ablation study (Section 31):** the one real false-automation case in the
  whole project (a resume containing a deliberate prompt-injection attempt)
  is wrongly approved by any configuration lacking an injection check or
  risk model, and correctly caught by every configuration that has one.
- **Automation-readiness score: 74.24/100**, tier **HUMAN_IN_THE_LOOP_READY**
  — deliberately not the top tier, because the project's own human-AI
  agreement numbers come from the same author writing both sides, and the
  system is built to say so rather than hide it.
- **0% false-automation rate** across 58 real "safe to automate" decisions
  in the dataset.

Full detail: `docs/19_final_engineering_report.md` (also published as a
shareable report/deck for presentation).

## 11. Project log and docs

- `docs/01_problem_scope_safety.md` — the problem, workflow choice, scope, safety rules
- `docs/02_decision_log.md` — every real design/technology decision, with reasoning
- `docs/03_established_vs_own_design.md` — established techniques vs. this project's own design
- `docs/04_architecture.md` → `docs/15_automation_readiness.md` — one doc per pipeline component
- `docs/16_failure_scenarios_dashboard.md` — the 10 forced failure scenarios and the dashboard
- `docs/17_requirements_traceability.md` — proof every brief requirement is actually met
- `docs/18_experiments_and_ablation.md` — Day 15 experiments and ablation study, in full
- `docs/19_final_engineering_report.md` — the complete final report
- `daily_log/` — one entry per day, each with real proof of completion (commands run, output shown)

## 12. Progress

- [x] Day 1 — Problem, workflow selection, safety
- [x] Day 2 — Event schema and architecture
- [x] Day 3 — Mock business environment
- [x] Day 4 — Workflow event logger
- [x] Day 5 — Workflow reconstruction engine
- [x] Day 6 — Decision and condition extraction
- [x] Day 7 — Automation generator
- [x] Day 8 — Shadow execution
- [x] Day 9 — Human–AI comparison engine
- [x] Day 10 — Confidence and risk scoring
- [x] Day 11 — Disagreement, exceptions, approval gates
- [x] Day 12 — Correction memory and versioning
- [x] Day 13 — Automation-readiness evaluation
- [x] Day 14 — Failure scenarios and dashboard
- [x] Day 15, Part A — Experiments and ablation study (`docs/18`)
- [x] Day 15, Part B — Final report and presentation

## 13. Status

Days 1-14 complete and committed. Day 15 is in its final stretch — the
experiments, ablation study, final report, and presentation are all built
and verified; only the demo script is left before Day 15 is committed as a
whole. 218/218 automated tests passing throughout. Every number in this
repository and its final report is generated by real, re-runnable code —
never hand-typed.
