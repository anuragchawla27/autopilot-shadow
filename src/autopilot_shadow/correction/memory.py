"""
Correction memory store (Day 12, Section 24).

Of Section 24's listed ways to use stored corrections ("retrieval-based
correction memory, rule updates, prompt/context updates, evaluation
dataset expansion, lightweight model adaptation"), this project
implements the first: a plain, retrievable store keyed by ACTION,
because that's the same granularity Day 10's risk model and Day 11's
exception detector already operate at — "has this action been
corrected before, and how?" is a directly useful question for a future
risk/confidence decision to ask. Section 24 is explicit that we must
NOT blindly retrain a model on every correction, so retrieval (not
adaptation) is the deliberately conservative choice here, same
reasoning Day 7 used to avoid LangGraph (D-004): the simplest
mechanism that satisfies the requirement, not the most sophisticated
one available.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .schema import CorrectionRecord


class CorrectionMemory:
    def __init__(self) -> None:
        self._records: list[CorrectionRecord] = []

    def add(self, record: CorrectionRecord) -> None:
        self._records.append(record)

    def all(self) -> list[CorrectionRecord]:
        return list(self._records)

    def for_action(self, action: str) -> list[CorrectionRecord]:
        return [r for r in self._records if r.workflow_context.get("action") == action]

    def retrieve_similar(self, action: str, top_n: int = 5) -> list[CorrectionRecord]:
        """Retrieval-based lookup: the most recent corrections for this
        same action, most recent first. Deliberately simple (no
        embeddings/semantic search) — see module docstring."""
        matches = self.for_action(action)
        return sorted(matches, key=lambda r: r.timestamp, reverse=True)[:top_n]

    def correction_rate_by_action(self) -> dict[str, dict]:
        """How often each action has actually been corrected (edited/
        rejected/escalated) vs. just approved — the honest signal Day
        10's historical_agreement.py computes for AGREEMENT; this is
        its mirror for CORRECTIONS specifically."""
        by_action: dict[str, int] = defaultdict(int)
        for r in self._records:
            by_action[r.workflow_context.get("action", "unknown")] += 1
        return {action: {"correction_count": n} for action, n in by_action.items()}

    def save(self, path: Path) -> None:
        path.write_text(json.dumps([r.as_dict() for r in self._records], indent=2, default=str))

    @classmethod
    def load(cls, path: Path) -> "CorrectionMemory":
        mem = cls()
        if not path.exists():
            return mem
        for d in json.loads(path.read_text()):
            mem.add(
                CorrectionRecord(
                    correction_id=d["correction_id"],
                    workflow_context=d["workflow_context"],
                    original_ai_decision=d["original_ai_decision"],
                    human_correction=d["human_correction"],
                    human_correction_detail=d["human_correction_detail"],
                    evidence=d["evidence"],
                    reason=d["reason"],
                    timestamp=d["timestamp"],
                    source=d["source"],
                )
            )
        return mem
