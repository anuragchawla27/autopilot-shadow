# 03 — Established Techniques vs Our Own Engineering Design

The project brief requires us to state which components use established techniques and which are our own design. This is a **living table**: it starts as a plan on Day 1 and is refined as each component is built.

> We do not claim to be the first system to learn workflows. Any citations below must be verified before use in the final report.

| Component | Established technique / prior art | Our engineering design (planned) |
|---|---|---|
| Workflow reconstruction | Process mining / process discovery from event logs | Mapping raw events into our own workflow schema, including decision points, exceptions and approvals |
| Decision extraction | Rule induction and pattern inference from examples | Three-way labelling of every rule: **explicit / inferred / unknown**, with evidence |
| Step classification (automate → blocked) | Risk-based triage | Explicit written criteria for 5 categories; labels are never assigned arbitrarily |
| Automation generation | Workflow engines, DAGs, LLM-based planning | JSON spec as source of truth, converted to an executable automation |
| Shadow execution | Shadow deployment / shadow mode in ML systems | Step-level interception of mock-tool calls; records proposed action, tool, extraction, decision, confidence and expected result |
| Human–AI comparison | Classification agreement measures | Five separate dimensions (action, data, decision, tool, outcome) that are never collapsed into one number |
| Confidence handling | Confidence thresholds; calibration analysis (e.g., expected calibration error) | Thresholds chosen by experiment; calibration checked because high confidence ≠ correctness |
| Risk model | Risk scoring from impact and likelihood factors | Factor set: reversibility, external impact, financial impact, privacy, uncertainty, confidence, historical agreement, potential harm, authorization; weights justified by experiments |
| Human-in-the-loop gates | Approval workflows | Approve / edit / reject / escalate gates that preserve the human decision |
| Correction memory | Retrieval-based memory | Stores original decision, correction, evidence, context, reason and timestamp; no blind retraining |
| Workflow versioning | Version control | Comparison of step, rule, risk, agreement and outcome changes across workflow versions |
| Readiness assessment | — | Decomposable score with a documented formula and four operational categories |
| Failure scenario testing | Fault injection / chaos testing | 10 named cases (Section 23), 8 driven by real Days 3/8-11 mechanisms, 2 (tool-selection, calibration) needed small new harnesses, documented as such |
| Tool output validation | Contract/schema validation | Minimum per-action output-key contract, closes Section 20's gap |
| Dashboard | Streamlit app patterns | 9-tab app reading only from prior-day results files; never recomputes a number |

## Status by day

| Component | Built on day | Final classification (established / adapted / own) |
|---|---|---|
| Event/workflow schemas | 2 | Adapted (Pydantic-validated, own field set) |
| Mock business environment | 3 | Own design (deterministic fault injection vocabulary) |
| Event logger / human demo policy | 4 | Own design |
| Workflow reconstruction | 5 | Adapted (process-mining concept, own merge/filter logic) |
| Decision extraction | 6 | Own design (explicit/inferred/unknown labelling) |
| Automation generator | 7 | Adapted (custom DAG executor, own classification criteria) |
| Shadow execution | 8 | Adapted (shadow-deployment concept, own step-interception design) |
| Human-AI comparison | 9 | Own design (5 separate dimensions, never collapsed) |
| Risk/confidence model | 10 | Own design (documented weighted formula, hard overrides) |
| Disagreement/exceptions/approval | 11 | Own design (structurally-enforced 4-state gate) |
| Correction memory/versioning | 12 | Adapted (plain retrieval, no embeddings) |
| Automation readiness | 13 | Own design (decomposable score, hard-gated HIGH tier) |
| Failure scenarios | 14 | Own design (10 cases, 2 new harnesses) |
| Tool output contracts | 14 | Own design (minimum per-action contract) |
| Dashboard | 14 | Adapted (Streamlit, own data-loader/presentation split) |
