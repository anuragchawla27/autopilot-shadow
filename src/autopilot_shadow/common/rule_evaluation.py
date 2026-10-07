"""
Generic rule/condition evaluation against a case context.

Built for Day 8 (shadow confidence must evaluate a Day 6 Rule's actual
conditions — field + operator + value — against a specific case, not
just compare dict values by field name). Written as a general utility
because Day 10's risk model will need the same operator-aware
evaluation against Rule objects.
"""

from __future__ import annotations

from autopilot_shadow.schemas.workflow import Condition, Rule

_OPERATORS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    "in": lambda a, b: a in b,
    "contains": lambda a, b: b in a,
}


def evaluate_condition(condition: Condition, context: dict) -> bool | None:
    """True/False, or None if `context` doesn't have this condition's
    field at all (caller should treat None as "can't evaluate, not a
    match" rather than guessing)."""
    if condition.field not in context:
        return None
    op = _OPERATORS.get(condition.operator)
    if op is None:
        raise ValueError(f"Unknown operator {condition.operator!r}")
    try:
        return bool(op(context[condition.field], condition.value))
    except TypeError:
        return None


def rule_matches(rule: Rule, context: dict) -> bool:
    """Evaluates every condition on `rule` against `context`, combined
    with AND/OR per `rule.condition_logic`. Any condition that can't be
    evaluated (missing field) makes the whole rule a non-match — we
    never guess a match on incomplete information."""
    if not rule.conditions:
        return False
    results = [evaluate_condition(c, context) for c in rule.conditions]
    if any(r is None for r in results):
        return False
    if rule.condition_logic == "OR":
        return any(results)
    return all(results)
