"""
Per-action historical human-AI agreement (Day 10, Section 10's
"historical human agreement" factor).

Day 9 already computed a dataset-level agreement rate across 5
dimensions, but never broken down BY ACTION — it didn't need to be for
Section 14's purposes. Section 10's risk model needs it per action,
because "how often has the AI historically agreed with the human on
THIS KIND OF STEP" is the actual signal — lumping
send_interview_invitation in with fetch_resume would hide exactly the
difference a risk model needs to surface.

HONEST CAVEAT (carried over from docs/11, repeated here because it
directly affects this model's output): this project's human policy and
AI logic were both written by the same person from the same rules, so
every action in the real 12-resume dataset currently shows 100%
historical agreement. That is a property of using fully-synthetic,
single-author data, not evidence that a real deployment would see the
same number. See `risk_model.py` for how this model deliberately
WEIGHTS historical agreement lowest of its 3 combined factors, precisely
because today's signal is this inflated.
"""

from __future__ import annotations

from collections import defaultdict


def per_action_agreement(comparisons: list[dict]) -> dict[str, dict]:
    """Returns {action: {"matched": int, "evaluable": int, "rate": float|None}}
    aggregated across every resume's aligned steps, using the same
    `match is not None` evaluability rule Day 9's `agreement.py` uses
    for action_agreement.
    """
    matched: dict[str, int] = defaultdict(int)
    evaluable: dict[str, int] = defaultdict(int)

    for comparison in comparisons:
        for step in comparison["steps"]:
            if step["match"] is None:
                continue
            action = step["action"]
            evaluable[action] += 1
            if step["match"]:
                matched[action] += 1

    result = {}
    for action in evaluable:
        rate = round(matched[action] / evaluable[action], 4) if evaluable[action] else None
        result[action] = {"matched": matched[action], "evaluable": evaluable[action], "rate": rate}
    return result
