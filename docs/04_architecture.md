# 04 — Event Schema & System Architecture (Day 2)

## 1. Event schema

The atomic unit of the whole system is an **Event** — one action taken during
a workflow demonstration. A demonstration is just an ordered list of Events
sharing a `demo_id`. Everything downstream (reconstruction, decision
extraction, shadow comparison) reads only from lists of Events, so getting
this right now avoids rework later.

Defined in `src/autopilot_shadow/schemas/event.py`, validated in
`tests/test_schemas_day2.py` (7/7 passing).

| Field | Type | Brief requirement covered |
|---|---|---|
| `event_id`, `demo_id`, `workflow_name`, `step_index` | identity/ordering | — (our addition, needed to group and sequence events) |
| `timestamp` | datetime | Section 5 |
| `actor`, `actor_type` | str, enum(human / ai_shadow / system) | Section 5 (`actor`); `actor_type` added so human and AI-shadow events can share one store and still be told apart for Day 9 comparison |
| `application` | str | Section 5 (`application/tool`) |
| `action` | str | Section 5 |
| `input`, `output` | dict | Section 5 |
| `decision` | `DecisionRecord` (nested) | Section 5 (`decision`); structured so Day 6 can extract rules programmatically instead of parsing text |
| `reasoning_summary` | optional str | Section 5 |
| `result` | str | Section 5 |
| `exception` | `ExceptionRecord` (nested) | Section 5 (`exception`); typed against the exact exception categories in Section 17/23 |
| `approval` | enum | Section 5 (`approval`); values match the four gate outcomes in Section 18 |
| `confidence` | optional float, 0-1 | Section 21 — only ever set on AI-shadow events (enforced by a validator) |
| `reversible` | optional bool | Section 10 — filled by the risk model on Day 10 |

**Why nested objects instead of flat strings:** `decision` and `exception`
could have been free-text fields. Making them typed sub-models means the
rule-extraction engine (Day 6) and exception-detection logic (Day 11) query
structured data instead of parsing sentences — this removes a whole class of
brittle string-matching bugs later.

## 2. Workflow schema

The **Workflow** is what the reconstruction engine (Day 5) produces from a
list of Events, and what the automation generator (Day 7) turns into
something executable. Defined in `src/autopilot_shadow/schemas/workflow.py`.

| Concept (Section 7 requirement) | How it's represented |
|---|---|
| Sequential steps | `WorkflowStep.next_steps` (single entry) |
| Branching / conditions | `next_steps` (multiple entries) + `Rule.conditions` |
| Loops | `WorkflowStep.loop_back_to` |
| Exceptions | `WorkflowStep.exception_handlers` |
| Human approvals | `WorkflowStep.requires_approval` |
| Tool calls | `WorkflowStep.application` / `.action` |
| Outputs | `WorkflowStep.outputs` |
| Decision extraction (Section 8) | `Rule.rule_type`: `explicit` / `inferred` / `unknown` — mandatory three-way split |
| Automation classification (Section 9) | `WorkflowStep.step_type` (5 categories) + `classification_reason` (never blank — Section 9 forbids arbitrary labels) |
| Risk (Section 10) | `WorkflowStep.risk` |
| Versioning (Section 25) | `Workflow.version` / `version_label` |

Both schemas were validated against realistic resume-screening data
(branching step, an explicit rule with two AND-ed conditions, a missing-document
exception, a rejected event with a bad field) — see the Day 2 proof output.

## 3. System architecture

Following the brief's recommended architecture (Section 33), adapted to name
our actual modules:

```
                     HUMAN WORKFLOW DEMONSTRATIONS (mock tools, Day 3)
                                    │
                                    ▼
                        EVENT LOGGER  (Day 4)
                     produces: list[Event]  ──────────────┐
                                    │                      │
                                    ▼                      │ (raw events kept
                  WORKFLOW RECONSTRUCTION ENGINE (Day 5)   │  for audit/replay)
                     produces: Workflow (UNCLASSIFIED)     │
                                    │                      │
                                    ▼                      │
                    DECISION EXTRACTION ENGINE (Day 6)     │
                fills: Rule.rule_type (explicit/inferred/unknown)
                                    │
                                    ▼
                    AUTOMATION GENERATOR (Day 7)
         fills: WorkflowStep.step_type + classification_reason
             produces: executable automation spec
                                    │
                                    ▼
              ┌─────────────────────┴─────────────────────┐
              ▼                                             ▼
   SHADOW EXECUTION ENGINE (Day 8)                 RISK + CONFIDENCE ENGINE (Day 10)
   runs automation against mock tools,             scores every proposed action;
   produces: list[Event] (actor_type=ai_shadow)    fills Event.confidence, .reversible
              │                                             │
              └─────────────────────┬─────────────────────┘
                                    ▼
                  HUMAN–AI COMPARISON ENGINE (Day 9)
        compares human Events vs ai_shadow Events per step
        (action / data / decision / tool / outcome agreement)
                                    │
                                    ▼
              ┌─────────────────────┴─────────────────────┐
              ▼                                             ▼
  DISAGREEMENT & EXCEPTION HANDLING (Day 11)        CORRECTION MEMORY (Day 12)
  creates investigation records; approval gates      stores human corrections
  (approve/edit/reject/escalate)                      workflow VERSIONING (Day 12)
              │                                             │
              └─────────────────────┬─────────────────────┘
                                    ▼
                 AUTOMATION-READINESS ENGINE (Day 13)
             decomposable score → 4 readiness categories
                                    │
                                    ▼
                    HUMAN APPROVAL  (ongoing, Day 11 gates)
                                    │
                                    ▼
              CONTROLLED EXECUTION  (approved steps only,
               still against mock tools per Section 19/22)
```

**Supporting/cross-cutting pieces (not in the main pipeline, used throughout):**

- `mock_env/` (Day 3) — the resume DB, CRM, email service, parser, ticket
  system that every stage above calls instead of a real system.
- `api/` (FastAPI) — exposes the pipeline stages as endpoints for the
  dashboard.
- `dashboard/` (Streamlit, built incrementally from Day 9) — reads from the
  same stores everything else writes to; it does not duplicate logic.
- `experiments/` and `results/` (Day 15, harness readied earlier) — run
  Experiments A–E and Ablation A–E against this same pipeline; `results/`
  only ever contains script-generated output (per S7 in the safety doc).

## 4. Data flow summary (plain words)

1. A human does the resume-screening workflow against mock tools. The event
   logger turns every action into an `Event`.
2. The reconstruction engine groups those events into a `Workflow` skeleton —
   steps and their order, nothing classified yet.
3. Decision extraction looks across many demonstrations of the same step and
   labels each rule explicit, inferred, or unknown.
4. The automation generator decides, per step, which of the 5 automation
   categories it belongs to, and turns the whole thing into something
   runnable.
5. That automation is run in shadow mode against the same mock tools the
   human used — it produces its own `Event`s (`actor_type=ai_shadow`) but
   never touches anything irreversible.
6. The comparison engine matches human events to AI-shadow events step by
   step and scores agreement on five separate dimensions.
7. Disagreements become investigation records; low-confidence, missing-data,
   or conflicting-info cases become exceptions; both route to a human
   approval gate that can approve/edit/reject/escalate.
8. Every correction a human makes is stored. Automation-readiness is
   computed from the accumulated evidence and decomposed into sub-scores,
   not just one number.
9. Only steps a human has actually approved, at a readiness level that
   justifies it, execute — and still only against mock tools in this
   project.

## 5. Why this shape

- **One schema, two representations.** Events are the ground truth log;
  Workflow is a derived, structured view. Keeping them separate means we can
  always re-run reconstruction differently without re-logging demonstrations.
- **AI-shadow events reuse the Event schema** instead of a separate type, so
  the comparison engine (Day 9) is a straightforward join on
  `(demo_id, step_index)` filtered by `actor_type`, not a translation layer
  between two different formats.
- **Nothing here executes anything yet.** Day 2 only defines shapes and
  validates them; Day 3 builds the mock tools these shapes will flow through.
