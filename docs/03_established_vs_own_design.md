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

## Status by day

To be updated as components are built.

| Component | Built on day | Final classification (established / adapted / own) |
|---|---|---|
| (filled in as we go) | | |
