"""
Preliminary per-action risk tagging (Day 7).

Section 9 requires that automation classification be based on EXPLICIT
criteria, never arbitrary labels. Those criteria need some notion of
risk/reversibility to apply at all — but the FULL weighted risk model
(reversibility, external impact, financial impact, privacy, uncertainty,
confidence, historical agreement, potential harm, authorization) is
Section 10's job, scheduled for Day 10.

This file is deliberately a SMALL, STATIC, HAND-JUSTIFIED table — a
placeholder just big enough to let Day 7's classifier make a defensible
decision today. Day 10 will replace it with a real weighted,
experiment-backed model. Treat every value here as provisional.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskTag:
    reversible: bool
    external_facing: bool  # does this action leave our own systems / reach a third party?
    risk: str  # "low" | "medium" | "high"
    justification: str


RISK_PROFILE: dict[str, RiskTag] = {
    "fetch_resume": RiskTag(
        reversible=True, external_facing=False, risk="low",
        justification="Read-only lookup against our own mock store; nothing is changed.",
    ),
    "extract_resume": RiskTag(
        reversible=True, external_facing=False, risk="low",
        justification="Pure parsing of already-fetched data; produces no side effects.",
    ),
    "check_experience": RiskTag(
        reversible=True, external_facing=False, risk="low",
        justification="Deterministic comparison against explicit JD config; no side effects.",
    ),
    "compare_skills": RiskTag(
        reversible=True, external_facing=False, risk="low",
        justification="Deterministic comparison against explicit JD config; no side effects.",
    ),
    "classify_candidate": RiskTag(
        reversible=True, external_facing=False, risk="medium",
        justification="No external effect yet, but this decision drives every downstream action "
        "(record status, whether an email goes out) — an error here propagates.",
    ),
    "update_candidate_record": RiskTag(
        reversible=True, external_facing=False, risk="low",
        justification="CRM write stays inside our own system and is correctable; history is kept (crm.py).",
    ),
    "send_interview_invitation": RiskTag(
        reversible=False, external_facing=True, risk="high",
        justification="Sends a message to a real third party (the candidate); cannot be unsent. "
        "Safety rule S3/S22: irreversible external actions always require explicit human approval.",
    ),
}
