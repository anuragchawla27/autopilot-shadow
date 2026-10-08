"""
Static, per-action risk factors (Day 10, Section 10).

Section 10 lists 8 factors a risk model should draw on: reversibility,
external impact, financial impact, privacy sensitivity, uncertainty,
confidence, historical human agreement, potential harm, and required
authorization. Of these, FOUR are properties of the ACTION ITSELF — they
don't change case to case (sending an interview email is always
irreversible and external-facing, whether the candidate is a strong or
weak match). The other factors (confidence, historical agreement) are
properties of a SPECIFIC CASE and live in `risk_model.py` instead.

This module is the permanent, documented version of those 4 static
factors. Day 7's `generator/risk_profile.py` already captured
reversibility and external_facing as a small placeholder table to let
Day 7's step-level classifier work — that file is left untouched (Day
7's classification still reads it, and still passes), but every value
there is reproduced and extended here with financial_impact and
privacy_sensitivity, because Day 10 needs the FULL factor set Section 10
asks for, not just the two Day 7 happened to need.

EVERY VALUE BELOW IS HAND-JUSTIFIED (see `justification` per action) —
none are arbitrary, per Section 10's own instruction not to use
unjustified weights.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionRiskFactors:
    reversible: bool
    external_facing: bool  # does this action leave our own systems / reach a third party?
    financial_impact: str  # "low" | "medium" | "high"
    privacy_sensitivity: str  # "low" | "medium" | "high"
    justification: str


ACTION_RISK_FACTORS: dict[str, ActionRiskFactors] = {
    "fetch_resume": ActionRiskFactors(
        reversible=True,
        external_facing=False,
        financial_impact="low",
        privacy_sensitivity="high",
        justification="Read-only lookup against our own mock store (reversible, internal, no cost) — "
        "but the record itself is a candidate's personal data (name, email, resume text), so privacy "
        "sensitivity is high even though nothing is changed or sent anywhere.",
    ),
    "extract_resume": ActionRiskFactors(
        reversible=True,
        external_facing=False,
        financial_impact="low",
        privacy_sensitivity="high",
        justification="Pure parsing of already-fetched data, no side effects, no cost — but produces "
        "structured personal fields (experience, skills, name) from the raw resume, same PII exposure "
        "as fetch_resume.",
    ),
    "check_experience": ActionRiskFactors(
        reversible=True,
        external_facing=False,
        financial_impact="low",
        privacy_sensitivity="low",
        justification="Deterministic numeric comparison against explicit JD config. Operates on a derived "
        "number (experience_years), not raw personal identifiers — lower privacy sensitivity than the "
        "extraction steps that handle the full PII record.",
    ),
    "compare_skills": ActionRiskFactors(
        reversible=True,
        external_facing=False,
        financial_impact="low",
        privacy_sensitivity="low",
        justification="Deterministic comparison against explicit JD config, same reasoning as "
        "check_experience — operates on a derived skills list, not the raw PII record.",
    ),
    "classify_candidate": ActionRiskFactors(
        reversible=True,
        external_facing=False,
        financial_impact="medium",
        privacy_sensitivity="medium",
        justification="No external effect yet and the step itself is correctable (classify_candidate "
        "doesn't write anywhere), but a wrong classification drives every downstream action for a real "
        "candidate — wasted interviewer time and hiring-pipeline cost if wrongly shortlisted, or a missed "
        "qualified candidate (legal/reputational exposure) if wrongly rejected. Medium, not low, financial "
        "impact; medium privacy sensitivity since the decision is made and recorded against an identified "
        "person's profile.",
    ),
    "update_candidate_record": ActionRiskFactors(
        reversible=True,
        external_facing=False,
        financial_impact="low",
        privacy_sensitivity="medium",
        justification="CRM write stays inside our own system, is correctable, and history is kept "
        "(crm.py) — low financial impact. Medium privacy sensitivity because the write stores a decision "
        "against an identified candidate's record, even though it isn't sent anywhere external.",
    ),
    "send_interview_invitation": ActionRiskFactors(
        reversible=False,
        external_facing=True,
        financial_impact="medium",
        privacy_sensitivity="high",
        justification="Sends a message to a real third party and cannot be unsent (Section 22's hard "
        "safety case) — the highest-impact action in this workflow on every factor: irreversible, "
        "external, triggers a real-world process (medium financial impact via interviewer/candidate time "
        "if sent wrongly), and is a direct personal communication to the candidate's own inbox (high "
        "privacy sensitivity).",
    ),
}


_IMPACT_LEVEL_SCORE = {"low": 0.0, "medium": 0.5, "high": 1.0}


def impact_score(factors: ActionRiskFactors) -> float:
    """Combines the 4 static factors into one impact score in [0, 1] —
    the average of: irreversibility (1 if NOT reversible, else 0),
    external-facing (1/0), financial impact, and privacy sensitivity.

    A plain average (not a weighted one) is the deliberate, simplest
    starting point for combining 4 factors that are all Section-10-named
    and none of which this project has evidence to rank above another —
    see docs/12 for why this is left as a documented, revisitable
    choice rather than hand-picked weights with no justification behind
    them (Section 10 forbids exactly that for the OVERALL formula, which
    is why the one real justified weighting in this model is reserved
    for combining impact with the case-specific factors in
    `risk_model.py`, where we DO have a concrete reason to weight one
    factor more than another).
    """
    components = [
        1.0 if not factors.reversible else 0.0,
        1.0 if factors.external_facing else 0.0,
        _IMPACT_LEVEL_SCORE[factors.financial_impact],
        _IMPACT_LEVEL_SCORE[factors.privacy_sensitivity],
    ]
    return round(sum(components) / len(components), 4)
