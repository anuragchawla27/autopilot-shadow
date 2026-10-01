"""
Decision & condition extraction engine (Day 6).

Section 8 of the brief makes this mandatory: every decision point the
system finds must be labelled EXPLICIT, INFERRED, or UNKNOWN — never
left unlabelled, never guessed.

THIS IS A GENUINELY SEPARATE STEP FROM DAY 4's HumanDemoPolicy.
Day 4's policy is the code that GENERATED the synthetic demonstrations
(it had to decide something to produce data at all). This engine reads
ONLY `demonstrations.json` + `job_description.json` — the same inputs a
real decision-extraction system would have — and re-derives rules from
evidence, with no import of and no knowledge of `human_demo.py`'s
internal logic. If this engine's output happened to match the
generator's logic perfectly, that would be circular; instead, as shown
below, it deliberately does NOT trust most of the generator's apparent
patterns, because most of them only have one supporting example.

LABELLING ALGORITHM (our own engineering design, not an established
technique — see docs/03):

1. EXPLICIT: a rule counts as explicit only when its condition maps
   directly onto a field the business already configured explicitly —
   `job_description.json`'s `required_experience_years` and
   `required_skills`. This matches Section 4's "explicit policy
   configuration" and Section 8's own worked example ("required_skill_
   present"). We do NOT call something explicit just because it's
   100% consistent in the data — consistency alone is evidence, not a
   stated rule.

2. INFERRED: a condition/outcome pattern that is NOT backed by explicit
   config, but is CONSISTENT (same outcome every time) across at least
   `MIN_EVIDENCE_FOR_INFERENCE` (= 2) independent demonstrations.

3. UNKNOWN: anything else — a pattern seen in only one demonstration
   (not enough evidence to generalize), or a pattern where the SAME
   evidence combination produced DIFFERENT outcomes across demos
   (contradictory). Section 8 explicitly allows the system to say "I
   cannot confidently reconstruct this" rather than force a guess.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from autopilot_shadow.schemas.workflow import Condition, Rule, RuleType

MIN_EVIDENCE_FOR_INFERENCE = 2


def _classify_events(events: list[dict]) -> list[dict]:
    return [e for e in events if e["action"] == "classify_candidate" and e.get("decision")]


def _evidence_key(evt: dict) -> tuple:
    inp = evt["input"]
    return (inp.get("experience_ok"), inp.get("skill_match_tier"), inp.get("injection_detected"))


def extract_rules(events: list[dict], job_description: dict) -> list[Rule]:
    """Returns a list of Rule objects, each labelled explicit/inferred/
    unknown, derived from the classify_candidate decision points in
    `events` plus the explicit configuration in `job_description`."""

    classify_events = _classify_events(events)

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for evt in classify_events:
        groups[_evidence_key(evt)].append(evt)

    rules: list[Rule] = []
    rule_counter = 0
    consumed_demo_ids: set[str] = set()

    # --- Rule A (EXPLICIT): experience below the configured threshold ---
    low_experience_group = [e for k, es in groups.items() for e in es if k[0] is False]
    if low_experience_group:
        rule_counter += 1
        outcomes = [e["decision"]["outcome"] for e in low_experience_group]
        then_outcome = max(set(outcomes), key=outcomes.count)
        rules.append(
            Rule(
                rule_id=f"rule_{rule_counter:02d}",
                description=(
                    f"IF experience_years < {job_description['required_experience_years']} "
                    f"(required_experience_years, explicit JD config) THEN {then_outcome}"
                ),
                conditions=[Condition(field="experience_years", operator="<", value=job_description["required_experience_years"])],
                condition_logic="AND",
                then_outcome=then_outcome,
                rule_type=RuleType.EXPLICIT,
                evidence_count=len(low_experience_group),
                source_demo_ids=sorted(set(e["demo_id"] for e in low_experience_group)),
            )
        )
        consumed_demo_ids |= set(e["demo_id"] for e in low_experience_group)

    # --- Rule B (EXPLICIT): experience OK AND all required skills present ---
    full_match_group = [
        e for k, es in groups.items() for e in es if k == (True, "full", False)
    ]
    if full_match_group:
        rule_counter += 1
        outcomes = [e["decision"]["outcome"] for e in full_match_group]
        then_outcome = max(set(outcomes), key=outcomes.count)
        rules.append(
            Rule(
                rule_id=f"rule_{rule_counter:02d}",
                description=(
                    f"IF experience_years >= {job_description['required_experience_years']} "
                    f"AND all required_skills {sorted(job_description['required_skills'])} present "
                    f"(explicit JD config) THEN {then_outcome}"
                ),
                conditions=[
                    Condition(field="experience_years", operator=">=", value=job_description["required_experience_years"]),
                    Condition(field="required_skills_present", operator="==", value=True),
                ],
                condition_logic="AND",
                then_outcome=then_outcome,
                rule_type=RuleType.EXPLICIT,
                evidence_count=len(full_match_group),
                source_demo_ids=sorted(set(e["demo_id"] for e in full_match_group)),
            )
        )
        consumed_demo_ids |= set(e["demo_id"] for e in full_match_group)

    # --- Remaining groups: INFERRED if consistent with >= 2 examples, else UNKNOWN ---
    for key, group_events in groups.items():
        remaining = [e for e in group_events if e["demo_id"] not in consumed_demo_ids]
        if not remaining:
            continue

        experience_ok, skill_tier, injection = key
        outcomes = [e["decision"]["outcome"] for e in remaining]
        distinct_outcomes = set(outcomes)
        rule_counter += 1

        description = (
            f"IF experience_ok={experience_ok} AND skill_match_tier={skill_tier!r} "
            f"AND injection_detected={injection} THEN ? "
            f"(observed outcome(s): {sorted(distinct_outcomes)})"
        )
        conditions = [
            Condition(field="experience_ok", operator="==", value=experience_ok),
            Condition(field="skill_match_tier", operator="==", value=skill_tier),
            Condition(field="injection_detected", operator="==", value=injection),
        ]

        if len(distinct_outcomes) == 1 and len(remaining) >= MIN_EVIDENCE_FOR_INFERENCE:
            rule_type = RuleType.INFERRED
            then_outcome = outcomes[0]
        elif len(distinct_outcomes) == 1:
            # consistent, but only one supporting example - not enough to generalize
            rule_type = RuleType.UNKNOWN
            then_outcome = outcomes[0]
        else:
            # contradictory evidence - different outcomes for the same evidence combo
            rule_type = RuleType.UNKNOWN
            then_outcome = "contradictory"

        rules.append(
            Rule(
                rule_id=f"rule_{rule_counter:02d}",
                description=description.replace("THEN ?", f"THEN {then_outcome}") if rule_type != RuleType.UNKNOWN or len(distinct_outcomes) == 1 else description,
                conditions=conditions,
                condition_logic="AND",
                then_outcome=then_outcome,
                rule_type=rule_type,
                evidence_count=len(remaining),
                source_demo_ids=sorted(set(e["demo_id"] for e in remaining)),
            )
        )

    return rules


def load_and_extract(data_dir: Path) -> list[Rule]:
    events = json.loads((data_dir / "demonstrations.json").read_text())
    job_description = json.loads((data_dir / "job_description.json").read_text())
    return extract_rules(events, job_description)
