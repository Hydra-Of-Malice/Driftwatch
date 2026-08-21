"""Repair verification: a healed scraper's output is never trusted, it is re-proven.

The preview returned at Bright Data's approval gate is replayed against the FULL
semantic contract — schema, invariants, semantics, continuity vs last-known-good.
Only that verdict (not the heal's own success status) decides approval.
"""

from __future__ import annotations

from ..contracts.engine import evaluate
from ..domain import ContractSpec, Verdict


def verify_preview(preview: dict | None, spec: ContractSpec, last_good: dict | None) -> Verdict:
    if preview is None:
        return Verdict(passed=False, confidence=0.0, gates=[], failing_fields=["(empty preview)"])
    return evaluate(preview, spec, last_good)
