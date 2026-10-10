"""
AUTOPILOT SHADOW dashboard (Day 14, Section 32).

Section 32 requires the dashboard to display: current workflow
structure, AI-proposed actions (shadow execution), human vs AI
comparison, disagreements, current automation readiness, risk
distribution, human corrections, and workflow versions over time.
Each panel below is its own tab, named directly after that list.

DESIGN RULE (carried from every prior day): this file only READS and
DISPLAYS results already produced by a `build_*.py` script from Days
5-14. It recomputes nothing — every number here traces back to a real
results/*.json file, never hand-typed or derived fresh in the UI layer
(S7). All data access goes through `data_loader.py`, which is tested
independently of Streamlit (tests/test_dashboard_data_day14.py).

Run: streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from dashboard import data_loader

st.set_page_config(page_title="AUTOPILOT SHADOW", layout="wide")

st.title("AUTOPILOT SHADOW")
st.caption(
    "AI Workflow Reconstruction, Shadow Execution & Automation Readiness — "
    "HR resume screening demo, synthetic data only."
)

loaded = data_loader.all_loaded()

# --- headline readiness banner (Day 13's own "surface this directly" note) ---
readiness = loaded["readiness"]
if readiness:
    score = readiness["shadow_score"]["shadow_score"]
    tier = readiness["readiness_decision"]["tier"]
    capped = readiness["shadow_score"]["hard_capped_by_false_automation"]
    c1, c2, c3 = st.columns([1, 1, 2])
    c1.metric("Shadow Score", f"{score:.2f} / 100")
    c2.metric("Readiness tier", tier.replace("_", " "))
    c3.markdown(
        f"**Decomposition is the point — never read {score:.2f} alone.** "
        f"{'A false automation was observed, hard-capping this score at 49 (Section 29).' if capped else 'No false automation observed in the real dataset (Section 29).'}"
    )

tabs = st.tabs(
    [
        "Workflow structure",
        "Shadow execution",
        "Human vs AI comparison",
        "Disagreements",
        "Automation readiness",
        "Risk distribution",
        "Human corrections",
        "Workflow versions",
        "Failure scenarios (Day 14)",
    ]
)

# 1. Current workflow structure -------------------------------------------
with tabs[0]:
    st.subheader("Current workflow structure")
    wf = loaded["workflow"]
    if wf:
        st.caption(f"{wf['workflow_name']} — version {wf['version']} ({wf.get('version_label', '')})")
        rows = [
            {
                "step": s["name"],
                "action": s["action"],
                "type": s["step_type"],
                "risk": s["risk"],
                "requires_approval": s["requires_approval"],
                "rules_attached": len(s.get("rules", [])),
            }
            for s in wf["steps"]
        ]
        st.dataframe(pd.DataFrame(rows), width="stretch")
    else:
        st.warning("data/workflow_classified.json not found.")

# 2. AI-proposed actions (Shadow Execution) --------------------------------
with tabs[1]:
    st.subheader("AI-proposed actions — shadow execution")
    st.caption(
        "Section 12: the AI proposes what it would do; nothing here is a real committed action "
        "(S3). Every row is a Day 8 shadow event."
    )
    events = loaded["shadow_run"]
    st.metric("Shadow events recorded", len(events))
    demo_ids = sorted({e["demo_id"] for e in events})
    chosen = st.selectbox("Resume (demo)", demo_ids)
    rows = [
        {
            "step": e["step_index"],
            "action": e["action"],
            "result": e["result"],
            "confidence": e.get("confidence"),
            "approval": e.get("approval"),
            "reasoning_summary": e.get("reasoning_summary"),
        }
        for e in events
        if e["demo_id"] == chosen
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch")

# 3. Human vs AI comparison -------------------------------------------------
with tabs[2]:
    st.subheader("Human vs AI comparison")
    st.caption(
        "Section 14: 5 separate agreement dimensions, never collapsed into one number. "
        "Real dataset is same-author (D-043) — 100% agreement here does not demonstrate "
        "independent human-AI agreement, see the readiness tab's caveat."
    )
    agreement = loaded["agreement_scores"]
    if agreement:
        st.json(agreement)
    comparisons = loaded["comparisons"]
    resume_ids = sorted({c["resume_id"] for c in comparisons})
    chosen_r = st.selectbox("Resume", resume_ids, key="comparison_resume")
    demo = next(c for c in comparisons if c["resume_id"] == chosen_r)
    rows = [
        {
            "action": s["action"],
            "human": s["human_value"],
            "ai": s["ai_value"],
            "match": s["match"],
            "ai_confidence": s.get("ai_confidence"),
        }
        for s in demo["steps"]
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch")

# 4. Disagreements -----------------------------------------------------------
with tabs[3]:
    st.subheader("Disagreements")
    disagreements = loaded["disagreements"]
    if not disagreements:
        st.info(
            "0 real disagreements in the 12-resume dataset (D-054's honest finding — the human "
            "demo policy and the AI classifier share an author). The mechanism itself is proven "
            "against hand-built synthetic mismatches (D-043/D-054) and Day 14's Case 6 — see the "
            "Failure scenarios tab."
        )
    else:
        st.dataframe(pd.DataFrame(disagreements), width="stretch")

# 5. Current automation readiness --------------------------------------------
with tabs[4]:
    st.subheader("Current automation readiness")
    if readiness:
        comp = readiness["shadow_score"]["components"]
        st.bar_chart(pd.Series(comp, name="score"))
        st.write(f"**Risk:** {readiness['shadow_score']['risk']}  |  **Reversibility:** {readiness['shadow_score']['reversibility']}")
        st.write(f"**Tier:** {readiness['readiness_decision']['tier']}")
        st.write(readiness["readiness_decision"]["reason"])
        with st.expander("Section 29 — critical metric: false automation rate"):
            far = readiness["shadow_score"]["false_automation_rate"]
            st.write(f"{far['false_automation_rate']} ({len(far['false_automations'])} / {far['automate_recommendations']} automate cases)")
        with st.expander("Companion metric: false escalation rate (discretionary gates only)"):
            fer = readiness["shadow_score"]["false_escalation_rate"]
            st.write(f"{fer['false_escalation_rate']} ({len(fer['would_have_matched_if_automated'])} / {fer['discretionary_gated_cases']} monitored cases, n=4 — caveat applies)")
    else:
        st.warning("results/day13_readiness_assessment.json not found.")

# 6. Risk distribution ---------------------------------------------------------
with tabs[5]:
    st.subheader("Risk distribution")
    risk_scores = loaded["risk_scores"]
    dist = data_loader.risk_distribution(risk_scores)
    st.bar_chart(pd.Series(dist, name="cases"))
    st.caption("Count of Day 10 risk-model recommendations across all 74 shadow-run action cases.")
    st.dataframe(pd.DataFrame(risk_scores), width="stretch", height=300)

# 7. Human corrections -----------------------------------------------------------
with tabs[6]:
    st.subheader("Human corrections")
    corrections = loaded["corrections"]
    if corrections and all(c.get("source") == "simulated_demo" for c in corrections):
        st.warning(
            "No live human-in-the-loop UI exists yet (D-057) — every record below is tagged "
            "source='simulated_demo': a fixed reference policy applied to Day 11's real approval "
            "queue, not a real human correction. Shown to prove the storage/retrieval mechanism "
            "works against real queue shapes, not as evaluation evidence."
        )
    rows = [
        {
            "correction_id": c["correction_id"],
            "action": c["workflow_context"]["action"],
            "resume_id": c["workflow_context"]["resume_id"],
            "original_recommendation": c["original_ai_decision"]["recommendation"],
            "human_correction": c["human_correction"],
            "source": c.get("source"),
        }
        for c in corrections
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch")

# 8. Workflow versions over time --------------------------------------------------
with tabs[7]:
    st.subheader("Workflow versions over time")
    versions = loaded["versions"]
    rows = [
        {
            "version": v["version"],
            "label": v["label"],
            "built_in_day": v["built_in_day"],
            "reached": v["reached"],
            "metrics": v["metrics"],
        }
        for v in versions
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch")
    not_reached = [v for v in versions if not v["reached"]]
    if not_reached:
        st.info(
            f"Version {not_reached[0]['version']} ({not_reached[0]['label']}) is honestly marked "
            "not yet reached (D-058) — no fabricated metrics stand in for it."
        )

# 9. Failure scenarios (Day 14's own task) -----------------------------------------
with tabs[8]:
    st.subheader("Failure scenarios — Section 23")
    report = loaded["failure_scenarios"]
    if report:
        st.metric("Cases failing safely", f"{report['n_passed']} / {report['n_cases']}")
        rows = [
            {
                "case": c["case_id"],
                "name": c["name"],
                "mechanism": c["mechanism"],
                "passed": c["passed"],
            }
            for c in report["cases"]
        ]
        st.dataframe(pd.DataFrame(rows), width="stretch")
        chosen_case = st.selectbox("Inspect a case", [c["case_id"] for c in report["cases"]])
        detail = next(c for c in report["cases"] if c["case_id"] == chosen_case)
        st.json(detail)
    else:
        st.warning("results/day14_failure_scenarios.json not found — run build_failure_report.py first.")

st.divider()
st.caption(
    "All data is synthetic (S1). Shadow mode performs no irreversible actions (S3). "
    "Every number above comes from a results/*.json file generated by running real code (S7)."
)
