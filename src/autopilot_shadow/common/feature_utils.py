"""
Shared feature-computation utilities.

These are pure computations (how do we measure skill overlap, how do we
spot a known prompt-injection pattern) used by BOTH the Day 4 human
demonstration policy and the Day 7 automation executor's handlers.
Sharing them here is deliberate and different from the Day 6 decision-
extraction independence requirement: this is "how a feature is
computed," not "which decision rule governs an outcome" — the thing
Day 6 must re-derive independently is the outcome mapping, not the
skill-matching arithmetic itself. See docs/09 for the full reasoning.
"""

from __future__ import annotations

_INJECTION_MARKERS = ("ignore all previous instructions", "ignore previous instructions")


def skill_match_tier(required_skills: set[str], candidate_skills: list[str]) -> str:
    """Returns 'full' (all required skills present), 'partial' (some),
    'none' (zero matched but skills were listed), or 'no_data' (no skills
    extracted at all)."""
    if not candidate_skills:
        return "no_data"
    matched = required_skills & set(s.lower() for s in candidate_skills)
    if matched == required_skills:
        return "full"
    if matched:
        return "partial"
    return "none"


def looks_like_prompt_injection(raw_text: str) -> bool:
    """Narrow, known-pattern check — a stand-in for a vigilant human
    reviewer who ignores embedded instructions in untrusted resume text
    (Safety rule S5). Not a general content filter."""
    lowered = raw_text.lower()
    return any(marker in lowered for marker in _INJECTION_MARKERS)
